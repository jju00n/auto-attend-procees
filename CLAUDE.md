# Auto Attendance Bot

회사 인트라넷 자동 출근 체크 봇 - AWS Lambda 기반

## 프로젝트 개요

평일 아침에 자동으로 회사 인트라넷에 로그인하여 출근 체크를 수행하고, 결과를 텔레그램으로 알림하는 서버리스 애플리케이션입니다.

## 주요 기능

- 인트라넷 자동 로그인 및 출근 체크
- 주말/공휴일 자동 건너뛰기 (공공데이터포털 API 활용)
- 인트라넷 휴가 일정 확인 (정기휴가 시 건너뛰기, 반차는 출근 체크)
- 텔레그램 봇을 통한 실시간 알림

## 기술 스택

- **런타임**: Python 3.x
- **플랫폼**: AWS Lambda
- **CI/CD**: Jenkins
- **주요 라이브러리**:
  - `requests`: HTTP 요청 처리
  - `python-telegram-bot`: 텔레그램 알림
  - `beautifulsoup4`: HTML 파싱 (휴가 정보 크롤링)
  - `freezegun`: 테스트용 시간 고정

## 프로젝트 구조

```
auto-attendance-bot/
├── lambda_function.py      # 메인 Lambda 핸들러
├── test_lambda_function.py # 단위 테스트
├── requirements.txt        # Python 의존성
├── Jenkinsfile            # CI/CD 파이프라인
└── venv/                  # Python 가상환경
```

## 환경 변수

AWS Lambda 콘솔에서 다음 환경 변수를 설정해야 합니다:

| 변수명 | 설명 |
|--------|------|
| `INTRANET_LOGIN_URL` | 인트라넷 로그인 처리 URL |
| `INTRANET_ATTEND_URL` | 출근 체크 API URL |
| `INTRANET_VACATION_URL` | 휴가 정보 페이지 URL |
| `USER_ID` | 인트라넷 로그인 ID |
| `USER_PW` | 인트라넷 로그인 비밀번호 |
| `BOT_TOKEN` | 텔레그램 봇 토큰 |
| `CHAT_ID` | 텔레그램 채팅 ID |
| `HOLIDAY_API_KEY` | 공공데이터포털 공휴일 API 키 |

## 개발 명령어

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
python -m unittest test_lambda_function.py
```

## 배포

Jenkins 파이프라인을 통해 자동 배포됩니다:

1. GitHub에서 코드 체크아웃
2. Python 의존성 설치
3. 단위 테스트 실행
4. Lambda 배포 패키지 생성
5. AWS Lambda 함수 업데이트

## 핵심 함수 설명

- `lambda_handler()`: Lambda 진입점. 주말/공휴일 체크 후 출근 프로세스 실행
- `run_clock_in_process()`: 로그인 → 휴가 확인 → 출근 체크 순차 실행
- `is_holiday()`: 공공데이터포털 API로 공휴일 여부 확인
- `is_vacation_on_intranet()`: 인트라넷 휴가 페이지 크롤링 (정기휴가만 체크)
- `send_telegram_message()`: 텔레그램 알림 발송

## 참고 사항

- 한국 시간(KST, UTC+9) 기준으로 동작
- 반차(오전반차/오후반차)는 휴가로 처리하지 않고 출근 체크 진행
- 로그인 실패 시 아이디/비밀번호 확인 필요
