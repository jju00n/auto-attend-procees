# Auto Attendance Bot

AWS Lambda 기반 회사 인트라넷 자동 출근 체크 봇

## 소개

매일 아침 자동으로 회사 인트라넷에 로그인하여 출근 체크를 수행하는 서버리스 애플리케이션입니다. 주말, 공휴일, 휴가일에는 자동으로 건너뛰며, 모든 결과는 텔레그램으로 실시간 알림됩니다.

## 주요 기능

- 평일 자동 출근 체크
- 주말 자동 건너뛰기
- 공휴일 자동 건너뛰기 (공공데이터포털 API 연동)
- 휴가일 자동 건너뛰기 (인트라넷 휴가 정보 크롤링)
- 반차(오전/오후반차) 시에는 정상 출근 체크
- 텔레그램 실시간 알림

## 기술 스택

| 구분 | 기술 |
|------|------|
| 런타임 | Python 3.x |
| 클라우드 | AWS Lambda |
| CI/CD | Jenkins |
| 알림 | Telegram Bot API |
| 외부 API | 공공데이터포털 공휴일 API |

## 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/jju00n/auto-attend-procees.git
cd auto-attend-procees
```

### 2. 가상환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. AWS Lambda 환경 변수 설정

AWS Lambda 콘솔에서 다음 환경 변수를 설정합니다:

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `INTRANET_LOGIN_URL` | 로그인 처리 URL | `https://intranet.company.com/loginProc` |
| `INTRANET_ATTEND_URL` | 출근 체크 API URL | `https://intranet.company.com/attend` |
| `INTRANET_VACATION_URL` | 휴가 정보 페이지 URL | `https://intranet.company.com/vacation` |
| `USER_ID` | 인트라넷 ID | - |
| `USER_PW` | 인트라넷 비밀번호 | - |
| `BOT_TOKEN` | 텔레그램 봇 토큰 | `123456:ABC-DEF...` |
| `CHAT_ID` | 텔레그램 채팅 ID | `123456789` |
| `HOLIDAY_API_KEY` | 공공데이터포털 API 키 | - |

### 4. AWS EventBridge 스케줄 설정

Lambda 함수를 평일 아침에 실행하도록 EventBridge 규칙을 생성합니다:

```
cron(0 0 ? * MON-FRI *)  # UTC 기준 00:00 = KST 09:00
```

## 테스트

```bash
# 단위 테스트 실행
python -m unittest test_lambda_function.py
```

## 배포

Jenkins 파이프라인을 통해 자동 배포됩니다:

1. **Checkout**: GitHub에서 최신 코드 가져오기
2. **Install**: Python 의존성 설치
3. **Test**: 단위 테스트 실행
4. **Package**: Lambda 배포 패키지(ZIP) 생성
5. **Deploy**: AWS Lambda 함수 업데이트

수동 배포 시:

```bash
# 패키지 생성
mkdir package
pip install --target ./package -r requirements.txt
cd package && zip -r ../deployment_package.zip .
cd .. && zip -g deployment_package.zip lambda_function.py

# Lambda 업로드
aws lambda update-function-code \
    --function-name auto-attendance-bot \
    --zip-file fileb://deployment_package.zip
```

## 동작 흐름

```
Lambda 실행
    │
    ├─ 주말? ──Yes──> 종료
    │
    ├─ 공휴일? ──Yes──> 텔레그램 알림 후 종료
    │
    ├─ 인트라넷 로그인
    │
    ├─ 정기휴가? ──Yes──> 텔레그램 알림 후 종료
    │
    ├─ 출근 체크 실행
    │
    └─ 결과 텔레그램 알림
```

## 텔레그램 알림 예시

- 출근 성공: `✅ 출근 체크 성공!`
- 공휴일: `🇰🇷 오늘은 공휴일(2025-01-01)이므로 출근 체크를 건너뜁니다.`
- 휴가일: `🌴 인트라넷에 휴가일(2025-01-02)로 확인되어 출근 체크를 건너뜁니다.`
- 실패: `❌ 출근 체크 실패! 이유: ...`

## 프로젝트 구조

```
auto-attendance-bot/
├── lambda_function.py      # 메인 Lambda 핸들러
├── test_lambda_function.py # 단위 테스트
├── requirements.txt        # Python 의존성
├── Jenkinsfile            # CI/CD 파이프라인
├── CLAUDE.md              # Claude Code 가이드
└── README.md              # 프로젝트 문서
```

## 라이선스

이 프로젝트는 개인 용도로 제작되었습니다.
