import json
import os
import requests
import telegram
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup # HTML 파싱을 위한 라이브러리

# --- AWS Lambda 환경 변수 ---
# Lambda 함수의 구성 설정에서 반드시 세팅해야 합니다.
INTRANET_LOGIN_URL = os.environ['https://intra.d2.co.kr/loginProc']
INTRANET_ATTEND_URL = os.environ['https://intra.d2.co.kr/intra/remote-work/attend']
INTRANET_VACATION_URL = os.environ['https://erp.d2.co.kr/Holiday/HolidayList.do'] # 휴가 페이지 URL
USER_ID = os.environ['pobylee']
USER_PW = os.environ['1234']
BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']
HOLIDAY_API_KEY = os.environ['HOLIDAY_API_KEY']

def send_telegram_message(text):
    """지정된 텔레그램 채팅으로 메시지를 보냅니다."""
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        bot.sendMessage(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print(f"텔레그램 메시지 전송 실패: {e}")

def is_holiday(today_str):
    """공공데이터포털 API를 사용하여 오늘이 대한민국의 공휴일인지 확인합니다."""
    try:
        year = today_str[:4]
        url = (f"[http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo](http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo)"
               f"?serviceKey={HOLIDAY_API_KEY}&solYear={year}&_type=json&numOfRows=100")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not items: return False
        holiday_dates = [str(item['locdate']) for item in items]
        return today_str.replace("-", "") in holiday_dates
    except Exception as e:
        print(f"공휴일 API 호출 오류: {e}")
        return False

def is_vacation_on_intranet(session):
    """로그인된 세션을 이용해 인트라넷 휴가 페이지를 크롤링하여 휴가 여부를 확인합니다."""
    try:
        # 로그인된 세션으로 휴가 페이지에 접속
        vacation_page_res = session.get(INTRANET_VACATION_URL)
        vacation_page_res.raise_for_status()

        # 페이지의 HTML 내용을 BeautifulSoup으로 파싱
        soup = BeautifulSoup(vacation_page_res.text, 'html.parser')

        # ==================== 사용자 수정 영역 ====================
        # 이 부분은 회사의 인트라넷 구조에 맞게 반드시 수정해야 합니다.
        # 아래는 예상 시나리오에 따른 예제 코드입니다.
        # Part 1.3에서 분석한 내용을 바탕으로 가장 적합한 코드를 선택하거나 조합하세요.

        # 예제 1: 달력에서 오늘 날짜(YYYY-MM-DD)를 찾고, 해당 셀에 'vacation' 클래스가 있는지 확인
        # today_cell = soup.find('td', {'data-date': today_str})
        # if today_cell and 'vacation' in today_cell.get('class', []):
        #     return True

        # 예제 2: 페이지 전체 텍스트에서 '오늘: 연차' 와 같은 특정 문자열이 있는지 확인
        if "정기휴가" in soup.get_text():
             return True

        # 예제 3: 'vacation_list'라는 id를 가진 목록에서 오늘 날짜가 포함된 항목 찾기
        # vacation_list = soup.find('ul', id='vacation_list')
        # if vacation_list and today_str in vacation_list.text:
        #     return True

        # =======================================================

        # 위 조건에 해당하지 않으면 휴가가 아닌 것으로 간주
        return False
    except Exception as e:
        print(f"인트라넷 크롤링 오류: {e}")
        # 크롤링 실패 시, 안전을 위해 근무일로 간주
        return False

def run_clock_in_process(today_str):
    """로그인, 휴가 확인, 출근 체크까지의 전체 프로세스를 처리합니다."""
    try:
        session = requests.Session()
        login_data = {'d2id': USER_ID, 'd2pass': USER_PW}
        
        login_res = session.post(INTRANET_LOGIN_URL, data=login_data)
        login_res.raise_for_status()
        if "로그인" in login_res.text or "비밀번호" in login_res.text:
             return "❌ 출근 체크 실패!\n이유: 로그인에 실패했습니다."
        print("로그인 성공.")
        
        # 로그인 성공 후, 휴가 여부 확인
        if is_vacation_on_intranet(session):
            return f"🌴 인트라넷에 휴가일({today_str})이 등록되어 있어 출근 체크를 건너뜁니다."

        # 휴가가 아니면 출근 체크 수행
        attend_res = session.post(INTRANET_ATTEND_URL)
        attend_res.raise_for_status()
        result_json = attend_res.json()
        if result_json.get('status') == 'success':
            return "✅ 출근 체크 성공!"
        else:
            return f"❌ 출근 체크 실패!\n서버 메시지: {result_json.get('msg', '알 수 없는 오류')}"
    except Exception as e:
        return f"❌ 출근 체크 실패!\n오류: {e}"

def lambda_handler(event, context):
    """스케줄에 따라 실행되며, 근무일인지 확인 후 출근 체크를 수행합니다."""
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_str = kst_now.strftime('%Y-%m-%d')
    
    if kst_now.weekday() >= 5:
        print(f"주말({today_str})이므로 건너뜁니다.")
        return
        
    if is_holiday(today_str):
        message = f"🇰🇷 오늘은 공휴일({today_str})이므로 출근 체크를 건너뜁니다."
        send_telegram_message(message)
        return

    # 주말/공휴일이 아니면 로그인 및 크롤링 프로세스 시작
    send_telegram_message(f"⏰ 근무일({today_str})입니다. 자동 출근 체크를 시작합니다.")
    result_message = run_clock_in_process(today_str)
    send_telegram_message(result_message)
    
    return {'statusCode': 200, 'body': json.dumps('Process finished.')}
