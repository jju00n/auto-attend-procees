import unittest
from unittest.mock import patch, Mock
import os

# 테스트 대상 파일을 임포트하기 전에 가짜 환경 변수를 설정해야 합니다.
os.environ['INTRANET_LOGIN_URL'] = '[http://fake-intranet.com/loginProc](http://fake-intranet.com/loginProc)'
os.environ['INTRANET_ATTEND_URL'] = '[http://fake-intranet.com/attend](http://fake-intranet.com/attend)'
os.environ['INTRANET_VACATION_URL'] = '[http://fake-intranet.com/vacation](http://fake-intranet.com/vacation)'
os.environ['USER_ID'] = 'test_user'
os.environ['USER_PW'] = 'test_pass'
os.environ['BOT_TOKEN'] = 'fake_token'
os.environ['CHAT_ID'] = '12345'
os.environ['HOLIDAY_API_KEY'] = 'fake_api_key'

# 이제 환경 변수가 설정되었으므로, 테스트 대상 파일을 임포트합니다.
import lambda_function

class TestLambdaFunction(unittest.TestCase):

    @patch('lambda_function.requests.get')
    @patch('lambda_function.requests.post')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_workday(self, mock_send_telegram, mock_post, mock_get):
        """ 시나리오 1: 평일 근무일일 때 정상적으로 출근 체크가 성공하는지 테스트 """
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "로그인 성공 페이지"
        mock_attend_response = Mock()
        mock_attend_response.status_code = 200
        mock_attend_response.json.return_value = {'status': 'success'}
        mock_post.side_effect = [mock_login_response, mock_attend_response]
        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = "<html><body>휴가 내역 없음</body></html>"
        mock_get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 2)
        last_call_args = mock_send_telegram.call_args[0]
        self.assertIn("✅ 출근 체크 성공!", last_call_args[0])

    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_holiday(self, mock_send_telegram):
        """ 시나리오 2: 공휴일일 때 출근 체크를 건너뛰는지 테스트 """
        with patch('lambda_function.is_holiday', return_value=True):
            lambda_function.lambda_handler({}, {})
        self.assertEqual(mock_send_telegram.call_count, 1)
        self.assertIn("공휴일", mock_send_telegram.call_args[0][0])

    @patch('lambda_function.requests.get')
    @patch('lambda_function.requests.post')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_vacation(self, mock_send_telegram, mock_post, mock_get):
        """ 시나리오 3: 휴가일일 때 출근 체크를 건너뛰는지 테스트 """
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "로그인 성공 페이지"
        mock_post.return_value = mock_login_response

        from datetime import datetime, timezone, timedelta
        today_str = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = f"<html><body><td>정기휴가</td></body></html>"
        mock_get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 2)
        self.assertIn("휴가일", mock_send_telegram.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
