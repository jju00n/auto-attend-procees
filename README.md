# Auto Attendance Bot

AWS Lambda 기반 회사 인트라넷 자동 출근 체크 봇

## 만든 이유

매일 아침 수동으로 출근 체크를 해야 하는데, 바쁜 업무 중에 놓치면 지각 처리가 되고 출결 수정 결재까지 올려야 하는 상황이 반복됐다. 반복적인 human error가 실제 업무 손실로 이어지는 구조를 자동화로 제거하고자 만들었다.

## 기술 선택 이유

### 왜 AWS Lambda (서버리스)인가

| 대안 | 문제점 |
|------|--------|
| EC2 상시 서버 | 하루 한 번 실행에 24시간 서버 유지는 비용 낭비 |
| 로컬 크론잡 | PC 절전/재부팅 시 실행 보장 안 됨, 신뢰성 없음 |
| **AWS Lambda** | 실행할 때만 과금, EventBridge로 스케줄링 기본 제공, 서버 관리 불필요 |

### 왜 Python인가

HTTP 요청, HTML 파싱, 크롤링이 핵심 작업인데 `requests`, `BeautifulSoup` 같은 라이브러리가 Java 대비 간결하다. Lambda 환경에서 Python의 cold start가 Java보다 빠르기 때문에 단발성 실행에도 유리하다.

## 기술 스택

| 구분 | 기술 |
|------|------|
| 런타임 | Python 3.x |
| 실행 환경 | AWS Lambda |
| 스케줄링 | AWS EventBridge (`cron(50 23 ? * SUN-THU *)` = KST 08:50 월~금) |
| CI/CD | GitHub Actions |
| 알림 | Telegram Bot API |
| 공휴일 판단 | 공공데이터포털 API |
| 휴가 판단 | 인트라넷 HTML 크롤링 (BeautifulSoup) |
| 테스트 | unittest + freezegun + unittest.mock |

## 동작 흐름

```
EventBridge (매일 KST 08:50, 월~금)
  └── lambda_handler()
        ├── 주말 여부 확인 → 주말이면 종료
        ├── is_holiday() → 공휴일이면 텔레그램 알림 후 종료
        └── run_clock_in_process()
              ├── 인트라넷 로그인
              ├── is_vacation_on_intranet() → 정기휴가면 스킵
              └── 출근 체크 API 호출 → 결과 텔레그램 알림
```

## 예외처리 설계

**기본 원칙: 불확실한 상태에서는 출근 체크를 진행하지 않는다**

| 상황 | 처리 방식 |
|------|----------|
| 공휴일 API 실패 / JSON 파싱 실패 | 출근 체크 중단 + 텔레그램 경고 |
| 휴가 크롤링 실패 | 출근 체크 중단 + 실패 메시지 전송 |
| 휴가 날짜 형식 오류 | 해당 행 스킵 후 출근 체크 진행, CloudWatch 경고 로그 |
| 로그인 실패 | 리다이렉트 URL `/login` 포함 여부로 판단 |
| 출근 체크 API 응답 이상 / 타임아웃 | 실패 메시지 반환 → 텔레그램 전송 |
| 텔레그램 전송 실패 | 예외를 삼키고 CloudWatch Logs에 `[WARN]` 기록 |

텔레그램이 실패하면 CloudWatch Logs를 최종 fallback으로 사용한다. 알림 수단 자체가 실패했을 때 또 다른 알림을 붙이면 끝이 없기 때문이다.

## 보안

- 아이디/비밀번호, API 키, 봇 토큰 등 민감 정보는 **Lambda 환경 변수**로 관리 (코드 하드코딩 금지)
- Lambda 실행 역할은 CloudWatch Logs 권한만 부여 (**최소 권한 원칙**)
- EventBridge → Lambda 호출 권한은 리소스 기반 정책으로 별도 관리

## 배포 (CI/CD)

`main` 브랜치에 push하면 GitHub Actions가 자동으로 실행된다.

```
push to main
  └── GitHub Actions
        ├── 단위 테스트 실행 → 실패 시 배포 중단
        ├── 의존성 포함 ZIP 패키징
        └── AWS Lambda 배포
```

> 초기엔 Jenkins로 구성했으나, Jenkins 서버용 EC2를 유지하는 게 비효율적이라 GitHub Actions으로 전환했다.

## 테스트

```bash
source venv/bin/activate
python -m unittest test_lambda_function.py -v
```

총 10개 케이스 커버:

**핵심 시나리오**
- 평일 출근 체크 성공
- 공휴일 스킵
- 공휴일 API 실패 시 중단
- 정기휴가 스킵
- 로그인 실패
- 텔레그램 실패 시 예외 없이 로그만 출력

**엣지 케이스**
- 공휴일 API JSON 파싱 실패 시 중단
- 휴가 날짜 형식 오류 시 해당 행 스킵 후 출근 체크 진행
- 출근 API 응답에 `status` 키 없는 경우 실패 메시지
- 네트워크 타임아웃 시 실패 메시지

## 환경 변수

AWS Lambda 콘솔에서 설정:

| 변수명 | 설명 |
|--------|------|
| `INTRANET_LOGIN_URL` | 인트라넷 로그인 처리 URL |
| `INTRANET_ATTEND_URL` | 출근 체크 API URL |
| `INTRANET_VACATION_URL` | 휴가 정보 페이지 URL |
| `USER_ID` | 인트라넷 로그인 ID |
| `USER_PW` | 인트라넷 로그인 비밀번호 |
| `BOT_TOKEN` | 텔레그램 봇 토큰 |
| `CHAT_ID` | 텔레그램 채팅 ID |
| `HOLIDAY_API_KEY` | 공공데이터포털 API 키 |

## 프로젝트 구조

```
auto-attend-procees/
├── lambda_function.py          # Lambda 핸들러 및 핵심 로직
├── test_lambda_function.py     # 단위 테스트
├── requirements.txt            # Python 의존성
├── .github/workflows/
│   └── deploy.yml             # GitHub Actions CI/CD 파이프라인
└── README.md
```

## 텔레그램 알림 예시

```
✅ 출근 체크 성공!
🇰🇷 오늘은 공휴일(2025-01-01)이므로 출근 체크를 건너뜁니다.
🌴 인트라넷에 휴가일(2025-08-15)로 확인되어 출근 체크를 건너뜁니다.
⚠️ 공휴일 API 호출 실패: ... 수동으로 확인해주세요.
❌ 출근 체크 실패! 이유: ...
```
