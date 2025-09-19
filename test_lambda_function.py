import unittest
from unittest.mock import patch, Mock
import os

os.environ['INTRANET_LOGIN_URL'] = '[http://fake-intranet.com/loginProc](http://fake-intranet.com/loginProc)'
os.environ['INTRANET_ATTEND_URL'] = '[http://fake-intranet.com/attend](http://fake-intranet.com/attend)'
os.environ['INTRANET_VACATION_URL'] = '[http://fake-intranet.com/vacation](http://fake-intranet.com/vacation)'
os.environ['USER_ID'] = 'test_user'
os.environ['USER_PW'] = 'test_pass'
os.environ['BOT_TOKEN'] = 'fake_token'
os.environ['CHAT_ID'] = '12345'
os.environ['HOLIDAY_API_KEY'] = 'fake_api_key'

import lambda_function

class TestLambdaFunction(unittest.TestCase):

    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_workday(self, mock_send_telegram, mock_session):
        """ 시나리오 1: 평일 근무일일 때 정상적으로 출근 체크가 성공하는지 테스트 """
        # --- 가짜 응답 설정 ---
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "메인 페이지입니다." # "로그인" 단어를 포함하지 않도록 수정

        mock_attend_response = Mock()
        mock_attend_response.status_code = 200
        mock_attend_response.json.return_value = {'status': 'success'}

        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = "<html><body><table><tbody></tbody></table></body></html>"

        # session.post와 session.get이 호출될 때 반환할 가짜 응답들을 설정
        mock_session.return_value.post.side_effect = [mock_login_response, mock_attend_response]
        mock_session.return_value.get.return_value = mock_vacation_response

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

    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_vacation(self, mock_send_telegram, mock_session):
        """ 시나리오 3: 휴가일일 때 출근 체크를 건너뛰는지 테스트 """
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "메인 페이지입니다." # "로그인" 단어를 포함하지 않도록 수정

        from datetime import datetime, timezone, timedelta
        today_str_dot = datetime.now(timezone(timedelta(hours=9))).strftime('%Y.%m.%d')
        mock_html = f"""
        <html><body><table><tbody>
          <tr><td>정기휴가</td><td>{today_str_dot}</td><td>{today_str_dot}</td><td>1.0일</td></tr>
        </tbody></table></body></html>
        """
        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = mock_html

        mock_session.return_value.post.return_value = mock_login_response
        mock_session.return_value.get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})

        self.assertEqual(mock_send_telegram.call_count, 2)
        self.assertIn("휴가일", mock_send_telegram.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
