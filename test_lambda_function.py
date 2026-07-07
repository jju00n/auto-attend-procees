import unittest
from unittest.mock import patch, Mock, AsyncMock
import os
from freezegun import freeze_time
import datetime

os.environ['INTRANET_LOGIN_URL'] = 'http://fake-intranet.com/loginProc'
os.environ['INTRANET_ATTEND_URL'] = 'http://fake-intranet.com/attend'
os.environ['INTRANET_VACATION_URL'] = 'http://fake-intranet.com/vacation'
os.environ['USER_ID'] = 'test_user'
os.environ['USER_PW'] = 'test_pass'
os.environ['BOT_TOKEN'] = 'fake_token'
os.environ['CHAT_ID'] = '12345'
os.environ['HOLIDAY_API_KEY'] = 'fake_api_key'

import lambda_function

VACATION_HTML_EMPTY = """
<html><body>
  <h2 class="sub_tit mt30 mt20">연차사용 내역</h2>
  <div class="table_h2">
    <table><thead><tr><th>번호</th><th>휴가구분</th><th>시작일</th><th>종료일</th><th>사용일</th></tr></thead>
    <tbody></tbody></table>
  </div>
</body></html>
"""

def make_vacation_html(vacation_type, start_date, end_date):
    return f"""
<html><body>
  <h2 class="sub_tit mt30 mt20">연차사용 내역</h2>
  <div class="table_h2">
    <table><thead><tr><th>번호</th><th>휴가구분</th><th>시작일</th><th>종료일</th><th>사용일</th></tr></thead>
    <tbody>
      <tr><td>1</td><td>{vacation_type}</td><td>{start_date}</td><td>{end_date}</td><td>1.0일</td></tr>
    </tbody></table>
  </div>
</body></html>
"""

class TestLambdaFunction(unittest.TestCase):

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_workday(self, mock_send_telegram, mock_session):
        """평일 근무일 출근 체크 성공"""
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "<html>메인 페이지</html>"

        mock_attend_response = Mock()
        mock_attend_response.status_code = 200
        mock_attend_response.json.return_value = {'status': 'success'}

        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = VACATION_HTML_EMPTY

        mock_session.return_value.post.side_effect = [mock_login_response, mock_attend_response]
        mock_session.return_value.get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 2)
        self.assertIn("✅ 출근 체크 성공!", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_holiday(self, mock_send_telegram):
        """공휴일이면 출근 체크 건너뜀"""
        with patch('lambda_function.is_holiday', return_value=True):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 1)
        self.assertIn("공휴일", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_holiday_api_failure(self, mock_send_telegram):
        """공휴일 API 실패 시 텔레그램 경고 후 출근 체크 중단"""
        with patch('lambda_function.is_holiday', side_effect=Exception("API 오류")):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 1)
        self.assertIn("공휴일 API 호출 실패", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_vacation(self, mock_send_telegram, mock_session):
        """정기휴가일이면 출근 체크 건너뜀"""
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "<html>메인 페이지</html>"

        today_str_dot = datetime.datetime.now().strftime('%Y.%m.%d')
        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = make_vacation_html("정기휴가", today_str_dot, today_str_dot)

        mock_session.return_value.post.return_value = mock_login_response
        mock_session.return_value.get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 2)
        self.assertIn("휴가일", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_login_failure(self, mock_send_telegram, mock_session):
        """로그인 실패 시 에러 메시지 전송"""
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "<html><body>로그인 페이지</body></html>"

        mock_session.return_value.post.return_value = mock_login_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 2)
        self.assertIn("로그인에 실패", mock_send_telegram.call_args[0][0])

    @patch('lambda_function.telegram.Bot')
    def test_send_telegram_failure(self, mock_bot):
        """텔레그램 전송 실패 시 예외 없이 로그만 출력"""
        mock_bot.return_value.send_message = AsyncMock(side_effect=Exception("텔레그램 오류"))

        try:
            lambda_function.send_telegram_message("테스트 메시지")
        except Exception:
            self.fail("텔레그램 실패 시 예외가 발생하면 안 됩니다.")

    # ── 엣지 케이스 ──────────────────────────────────────────

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.get')
    @patch('lambda_function.send_telegram_message')
    def test_holiday_api_invalid_json(self, mock_send_telegram, mock_requests_get):
        """공휴일 API 응답은 왔지만 JSON 파싱 실패 시 출근 체크 중단"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = Exception("JSON 파싱 오류")
        mock_requests_get.return_value = mock_response

        lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 1)
        self.assertIn("공휴일 API 호출 실패", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.get')
    def test_holiday_api_retry_success(self, mock_requests_get):
        """공휴일 API가 2번 타임아웃 후 3번째에 성공하면 재시도로 결과 반환"""
        import requests as req
        mock_success = Mock()
        mock_success.raise_for_status = Mock()
        mock_success.json.return_value = {
            'response': {'body': {'items': {'item': [{'locdate': 20250918}]}}}
        }
        mock_requests_get.side_effect = [
            req.exceptions.Timeout("타임아웃 1"),
            req.exceptions.Timeout("타임아웃 2"),
            mock_success,
        ]

        result = lambda_function.is_holiday("2025-09-18")

        self.assertTrue(result)
        self.assertEqual(mock_requests_get.call_count, 3)

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.get')
    def test_holiday_api_retry_exhausted(self, mock_requests_get):
        """공휴일 API가 3번 모두 타임아웃하면 마지막 예외를 전파"""
        import requests as req
        mock_requests_get.side_effect = req.exceptions.Timeout("타임아웃")

        with self.assertRaises(req.exceptions.Timeout):
            lambda_function.is_holiday("2025-09-18")

        self.assertEqual(mock_requests_get.call_count, 3)

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_vacation_invalid_date_format(self, mock_send_telegram, mock_session):
        """휴가 테이블 날짜 형식이 올바르지 않아도 출근 체크는 진행"""
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "<html>메인 페이지</html>"

        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = make_vacation_html("정기휴가", "2025/09/18", "2025/09/18")  # 잘못된 형식

        mock_attend_response = Mock()
        mock_attend_response.status_code = 200
        mock_attend_response.json.return_value = {'status': 'success'}

        mock_session.return_value.post.side_effect = [mock_login_response, mock_attend_response]
        mock_session.return_value.get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertIn("✅ 출근 체크 성공!", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_attend_api_unexpected_response(self, mock_send_telegram, mock_session):
        """출근 체크 API 응답에 status 키가 없는 경우 실패 메시지 전송"""
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "<html>메인 페이지</html>"

        mock_attend_response = Mock()
        mock_attend_response.status_code = 200
        mock_attend_response.json.return_value = {'result': 'ok'}  # status 키 없음

        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = VACATION_HTML_EMPTY

        mock_session.return_value.post.side_effect = [mock_login_response, mock_attend_response]
        mock_session.return_value.get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertIn("❌ 출근 체크 실패!", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_network_timeout(self, mock_send_telegram, mock_session):
        """네트워크 타임아웃 발생 시 실패 메시지 전송"""
        import requests as req
        mock_session.return_value.post.side_effect = req.exceptions.Timeout("타임아웃")

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertIn("❌ 출근 체크 실패!", mock_send_telegram.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
