import unittest
from unittest.mock import patch, Mock
import os
from freezegun import freeze_time
import datetime

# 테스트 실행 전에 환경 변수를 설정합니다.
os.environ['INTRANET_LOGIN_URL'] = 'http://fake-intranet.com/loginProc'
os.environ['INTRANET_ATTEND_URL'] = 'http://fake-intranet.com/attend'
os.environ['INTRANET_VACATION_URL'] = 'http://fake-intranet.com/vacation'
os.environ['USER_ID'] = 'test_user'
os.environ['USER_PW'] = 'test_pass'
os.environ['BOT_TOKEN'] = 'fake_token'
os.environ['CHAT_ID'] = '12345'
os.environ['HOLIDAY_API_KEY'] = 'fake_api_key'

# lambda_function 모듈을 임포트합니다.
import lambda_function

class TestLambdaFunction(unittest.TestCase):

    @freeze_time("2025-09-18 10:00:00")  # 주중 평일로 강제
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_workday(self, mock_send_telegram, mock_session):
        """ 평일 근무일 출근 체크 """
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        # (수정됨) 실제 코드가 기대하는 로그인 성공 응답으로 변경
        mock_login_response.text = "<html><script>document.location.href='/'</script></html>"

        mock_attend_response = Mock()
        mock_attend_response.status_code = 200
        mock_attend_response.json.return_value = {'status': 'success'}

        mock_vacation_response = Mock()
        mock_vacation_response.status_code = 200
        mock_vacation_response.text = "<html><body><table><tbody></tbody></table></body></html>"

        mock_session.return_value.post.side_effect = [mock_login_response, mock_attend_response]
        mock_session.return_value.get.return_value = mock_vacation_response

        with patch('lambda_function.is_holiday', return_value=False):
            lambda_function.lambda_handler({}, {})
        
        # 성공 시에는 텔레그램 메시지가 1번만 발송되어야 합니다 (시작 메시지 제외 시)
        # 만약 시작/종료 메시지를 모두 보낸다면 2가 맞습니다. 로직에 따라 조정하세요.
        self.assertIn("✅ 출근 체크 성공!", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")  # 평일로 강제
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_holiday(self, mock_send_telegram):
        """ 공휴일이면 출근 체크 건너뜀 """
        with patch('lambda_function.is_holiday', return_value=True):
            lambda_function.lambda_handler({}, {})
        
        self.assertIn("공휴일", mock_send_telegram.call_args[0][0])

    @freeze_time("2025-09-18 10:00:00")  # 평일로 강제
    @patch('lambda_function.requests.Session')
    @patch('lambda_function.send_telegram_message')
    def test_lambda_handler_vacation(self, mock_send_telegram, mock_session):
        """ 휴가일이면 출근 체크 건너뜀 """
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        # (수정됨) 실제 코드가 기대하는 로그인 성공 응답으로 변경
        mock_login_response.text = "<html><script>document.location.href='/'</script></html>"

        # 오늘 날짜와 동일하게 휴가 등록
        today_str_dot = datetime.datetime.now().strftime('%Y.%m.%d')
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

        self.assertIn("휴가일", mock_send_telegram.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
