import json
import os
import requests
import telegram
import asyncio
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup


# --- AWS Lambda 환경 변수 (나중에 AWS 콘솔에서 설정) ---
INTRANET_LOGIN_URL = os.environ['INTRANET_LOGIN_URL']
INTRANET_ATTEND_URL = os.environ['INTRANET_ATTEND_URL']
INTRANET_VACATION_URL = os.environ['INTRANET_VACATION_URL']
USER_ID = os.environ['USER_ID']
USER_PW = os.environ['USER_PW']
BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']
HOLIDAY_API_KEY = os.environ['HOLIDAY_API_KEY']

def send_telegram_message(text):
    """텔레그램으로 메시지를 보내는 함수"""
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        asyncio.run(bot.send_message(chat_id=CHAT_ID, text=text))
    except Exception as e:
        print(f"[WARN] 텔레그램 알림 전송 실패: {e}")

def is_holiday(today_str):
    """공공데이터포털 API를 이용해 오늘이 공휴일인지 확인하는 함수"""
    year = today_str[:4]
    url = f"https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo?serviceKey={HOLIDAY_API_KEY}&solYear={year}&_type=json&numOfRows=100"
    # 공공데이터포털 API는 응답 지연이 잦아 최대 3회 재시도
    max_retries = 3
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            items = response.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            holiday_dates = [str(item['locdate']) for item in items]
            return today_str.replace("-", "") in holiday_dates
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"[WARN] 공휴일 API 호출 실패 (시도 {attempt}/{max_retries}): {e}")
    raise last_error

def is_vacation_on_intranet(session, today_str):
    """인트라넷 휴가 페이지를 크롤링하여 오늘이 휴가일인지 확인하는 함수"""
    response = session.get(INTRANET_VACATION_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    today_date = datetime.strptime(today_str, '%Y-%m-%d').date()

    header = soup.find('h2', string=lambda t: t and '연차사용 내역' in t)
    if not header:
        raise ValueError("'연차사용 내역' 테이블을 찾을 수 없습니다. 페이지 구조가 변경되었을 수 있습니다.")

    table = header.find_next('table')
    for row in table.find('tbody').find_all('tr'):
        cols = [ele.text.strip() for ele in row.find_all('td')]
        if len(cols) > 3:
            vacation_type = cols[1]   # 휴가구분
            start_date_str = cols[2]  # 시작일
            end_date_str = cols[3]    # 종료일
            if '정기휴가' in vacation_type:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y.%m.%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y.%m.%d').date()
                    if start_date <= today_date <= end_date:
                        return True
                except ValueError:
                    print(f"[WARN] 날짜 변환 실패: {start_date_str}, {end_date_str}")
                    continue
    return False

def run_clock_in_process(today_str):
    """로그인, 휴가 확인, 출근 체크를 순차적으로 실행하는 메인 프로세스"""
    try:
        session = requests.Session()
        login_data = {'d2Id': USER_ID, 'd2Pass': USER_PW}
        login_res = session.post(INTRANET_LOGIN_URL, data=login_data)
        login_res.raise_for_status()
        if "로그인" in login_res.text or "Login" in login_res.text:
            return "❌ 출근 체크 실패!\n이유: 로그인에 실패했습니다. 아이디/비밀번호를 확인하세요."

        if is_vacation_on_intranet(session, today_str):
            return f"🌴 인트라넷에 휴가일({today_str})로 확인되어 출근 체크를 건너뜁니다."

        attend_res = session.post(INTRANET_ATTEND_URL)
        attend_res.raise_for_status()
        result_json = attend_res.json()
        msg = result_json.get('msg', '')
        if result_json.get('status') == 'success':
            return "✅ 출근 체크 성공!"
        elif '이미 등록' in msg:
            return "✅ 이미 출근 체크가 완료되어 있습니다."
        else:
            return f"❌ 출근 체크 실패!\n서버 메시지: {msg or '알 수 없는 오류'}"
    except requests.exceptions.RequestException as e:
        return f"❌ 출근 체크 실패!\n이유: 네트워크 오류가 발생했습니다. ({e})"
    except Exception as e:
        return f"❌ 출근 체크 실패!\n오류 발생: {e}"

def lambda_handler(event, context):
    """AWS Lambda가 실행하는 메인 핸들러 함수"""
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_str = kst_now.strftime('%Y-%m-%d')

    if kst_now.weekday() >= 5:
        print(f"주말({today_str})이므로 건너뜁니다.")
        return

    try:
        if is_holiday(today_str):
            send_telegram_message(f"🇰🇷 오늘은 공휴일({today_str})이므로 출근 체크를 건너뜁니다.")
            return
    except Exception as e:
        send_telegram_message(f"⚠️ 공휴일 API 호출 실패: {e}\n불확실한 상태이므로 출근 체크를 중단합니다. 수동으로 확인해주세요.")
        return

    send_telegram_message(f"⏰ 근무일({today_str})입니다. 자동 출근 체크를 시작합니다.")
    result_message = run_clock_in_process(today_str)
    send_telegram_message(result_message)

    return {'statusCode': 200, 'body': json.dumps('Process finished.')}
