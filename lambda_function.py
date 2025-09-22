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

# 주석 테스트 #
def send_telegram_message(text):
    """텔레그램으로 메시지를 보내는 함수 (최신 비동기 방식)"""
    bot = telegram.Bot(token=BOT_TOKEN)
    asyncio.run(bot.send_message(chat_id=CHAT_ID, text=text))

def is_holiday(today_str):
    """공공데이터포털 API를 이용해 오늘이 공휴일인지 확인하는 함수"""
    response = None
    try:
        year = today_str[:4]
        url = f"http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo?serviceKey={HOLIDAY_API_KEY}&solYear={year}&_type=json&numOfRows=100"
        print(f"Requesting Holiday API URL: {url}") # 디버깅을 위해 URL 출력
        response = requests.get(url, timeout=10)
        response.raise_for_status() # HTTP 에러가 있으면 예외 발생

        items = response.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        holiday_dates = [str(item['locdate']) for item in items]
        return today_str.replace("-", "") in holiday_dates
    except Exception as e:
        print(f"공휴일 API 호출 오류: {e}")
        if response is not None:
            print(f"Raw API Response Text: {response.text}") # 디버깅을 위해 실제 응답 내용 출력
        return False

def is_vacation_on_intranet(session, today_str):
    """인트라넷 휴가 페이지를 크롤링하여 오늘이 휴가일인지 확인하는 함수"""
    try:
        response = session.get(INTRANET_VACATION_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # 오늘 날짜를 datetime 객체로 변환 (비교를 위해)
        today_date = datetime.strptime(today_str, '%Y-%m-%d').date()
        # "연차사용 내역" 테이블을 찾습니다.
        tables = soup.find_all('table')
        for table in tables:
            # 테이블의 각 행(row)을 순회합니다. (헤더는 건너뜁니다)
            for row in table.find('tbody').find_all('tr'):
                # 각 행의 열(column) 데이터를 리스트로 추출합니다.
                cols = [ele.text.strip() for ele in row.find_all('td')]
                # 열의 개수가 충분한지 확인하여 오류를 방지합니다.
                if len(cols) > 3:
                    vacation_type = cols[0]  # 휴가구분 (이미지상 첫번째 열)
                    start_date_str = cols[1] # 시작일 (이미지상 두번째 열)
                    end_date_str = cols[2]   # 종료일 (이미지상 세번째 열)
                    # 휴가 구분이 '정기휴가'인지 확인합니다.
                    if '정기휴가' in vacation_type:
                        # 날짜 문자열(YYYY.MM.DD)을 datetime 객체로 변환합니다.
                        start_date = datetime.strptime(start_date_str, '%Y.%m.%d').date()
                        end_date = datetime.strptime(end_date_str, '%Y.%m.%d').date()
                        # 오늘 날짜가 휴가 기간에 포함되는지 확인합니다.
                        if start_date <= today_date <= end_date:
                            return True # 휴가일이 맞으므로 True를 반환하고 함수를 종료합니다.
        # 모든 휴가 기록을 확인했지만 해당 사항이 없으면 False를 반환합니다.
        return False
    except Exception as e:
        print(f"휴가 크롤링 오류: {e}")
        return False

def run_clock_in_process(today_str):
    """로그인, 휴가 확인, 출근 체크를 순차적으로 실행하는 메인 프로세스"""
    try:
        session = requests.Session()
        
        # 1. (수정됨) 데이터의 KEY를 HTML의 name 속성과 대소문자까지 정확히 일치시킵니다.
        login_data = {'d2Id': USER_ID, 'd2Pass': USER_PW}
        
        login_res = session.post(INTRANET_LOGIN_URL, data=login_data)
        print("로그인 응답 코드:", login_res.status_code)
        # print("로그인 응답 텍스트:", login_res.text) # 디버깅 시에만 활성화
        login_res.raise_for_status()

        # 2. (수정됨) 성공/실패 확인 로직을 변경합니다.
        # 실패 조건: 응답에 메인 페이지('/')로 이동하라는 스크립트가 없는 경우
        if "document.location.href='/'" not in login_res.text:
            return "❌ 출근 체크 실패!\n이유: 로그인에 실패했습니다. 아이디/비밀번호를 확인하세요."
        
        print("✅ 로그인 성공!")

        if is_vacation_on_intranet(session, today_str):
            return f"🌴 인트라넷에 휴가일({today_str})로 확인되어 출근 체크를 건너뜁니다."

        attend_res = session.post(INTRANET_ATTEND_URL)
        print("출근 등록 응답 코드:", attend_res.status_code)
        # print("출근 등록 응답 텍스트:", attend_res.text) # 디버깅 시에만 활성화
        attend_res.raise_for_status()
        
        result_json = attend_res.json()
        if result_json.get('status') == 'success':
            return "✅ 출근 체크 성공!"
        else:
            return f"❌ 출근 체크 실패!\n서버 메시지: {result_json.get('msg', '알 수 없는 오류')}"
            
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

    if is_holiday(today_str):
        message = f"🇰🇷 오늘은 공휴일({today_str})이므로 출근 체크를 건너뜁니다."
        send_telegram_message(message)
        return

    send_telegram_message(f"⏰ 근무일({today_str})입니다. 자동 출근 체크를 시작합니다.")
    result_message = run_clock_in_process(today_str)
    send_telegram_message(result_message)

    return {'statusCode': 200, 'body': json.dumps('Process finished.')}