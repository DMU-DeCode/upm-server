# 🖥️ UPM — Universal PC Manager · Global Server

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)

**동양미래대학교 컴퓨터소프트웨어공학과 졸업작품**  
PC 하드웨어 실시간 모니터링 및 원격 최적화 시스템 — **서버 인프라 파트 (Tier 2)**

</div>

---

## 📌 목차

- [프로젝트 개요](#overview)
- [시스템 아키텍처](#architecture)
- [기술 스택](#tech-stack)
- [프로젝트 구조](#structure)
- [서버 기능 상세](#features)
- [🧠 최적화 알고리즘 (Smart Cleanup)](#algorithm)
- [API 엔드포인트 명세](#api)
- [데이터베이스 구조](#database)
- [실시간 웹 대시보드](#dashboard)
- [설치 및 배포 가이드](#installation)
- [외부 네트워크 협업 가이드 (ngrok)](#ngrok)

---

<a id="overview"></a>
## 📝 1. 프로젝트 개요

| 기능 | 설명 |
|------|------|
| **실시간 리소스 모니터링** | C# WPF 에이전트가 수집하는 CPU / RAM / GPU 메트릭을 지연 없이 수신 |
| **시계열 데이터 영구 보관** | 모든 텔레메트리 로그를 MySQL에 안정적으로 적재하여 통계 분석 기반 확보 |
| **비동기 고성능 아키텍처** | FastAPI Async/Await 이벤트 루프로 다수 클라이언트 요청을 블로킹 없이 동시 처리 |
| **최적화 룰셋 중앙 배포** | 프로세스 화이트리스트/블랙리스트 기반 글로벌 최적화 규칙을 실시간으로 클라이언트에 공급 |

---

<a id="architecture"></a>
## 🌐 2. 시스템 아키텍처

UPM은 **클라이언트(Agent) — 서버(Global Server) — 모바일/브라우저(Dashboard)** 로 연결되는 3-Tier 아키텍처입니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                        UPM 전체 시스템                           │
│                                                                  │
│  ┌──────────────┐  HTTP POST  ┌──────────────────────────────┐  │
│  │  PC Agent    │ ──────────► │     UPM Global Server        │  │
│  │ (C# / WPF)   │             │    (Python / FastAPI)        │  │
│  │              │  HTTP GET   │                              │  │
│  │ ▸ CPU 사용률  │ ◄────────── │  ┌────────────────────────┐  │  │
│  │ ▸ RAM 사용률  │  최적화 룰셋 │  │   MySQL Database       │  │  │
│  │ ▸ GPU 사용률  │             │  │   (telemetry_logs)     │  │  │
│  └──────────────┘             │  └────────────────────────┘  │  │
│                               │                              │  │
│  ┌──────────────┐  HTTP GET   │  ┌────────────────────────┐  │  │
│  │   Browser    │ ──────────► │  │    Web Dashboard       │  │  │
│  │ (관리자/모바일) │             │  │   (HTML / Chart.js)   │  │  │
│  └──────────────┘             │  └────────────────────────┘  │  │
│                               └──────────────────────────────┘  │
│                                                                  │
│  ── 로컬망(LAN) 기반 데이터 수집 가속화 ──────────────────────── │
│  ── 외부망 광역 라우팅 (ngrok 터널링 연동) ───────────────────── │
└─────────────────────────────────────────────────────────────────┘
```

### 🛰️ 구체적인 연결 메커니즘

**외부망 인프라 (Client ↔ Server)**  
포트 포워딩이 제한된 환경에서 ngrok 역방향 프록시 터널링으로 외부망 HTTPS 요청을 내부 서버 8000번 포트로 릴레이합니다.

**실시간 데이터 파이프라인 (Client → Server → DB)**  
C# 에이전트가 Windows Performance Counter와 NVML API로 자원을 계측하고, JSON 패킷으로 조립하여 비동기 HTTP 요청으로 전송합니다.

**모니터링 관제 (Server → Dashboard)**  
관리자 대시보드의 Fetch API 엔진이 10초 주기로 백엔드 로그 API를 폴링하여 Chart.js와 바인딩된 실시간 UI를 갱신합니다.

---

<a id="tech-stack"></a>
## 🛠️ 3. 기술 스택

| 분류 | 기술 |
|------|------|
| Language | Python 3.11+ |
| Async Web Framework | FastAPI (고성능 ASGI, OpenAPI 자동 문서화) |
| Dashboard Server | Flask (경량 웹 모듈 기반 대시보드 렌더링) |
| ORM | SQLAlchemy 2.0+ (비동기 쿼리 및 커넥션 풀링 최적화) |
| DB Driver | PyMySQL (MySQL / MariaDB 연동 순수 파이썬 드라이버) |
| Data Validation | Pydantic v2 (타입 캐스팅 및 JSON 스키마 검증 자동화) |
| Database | MySQL 8.0 / MariaDB |
| Containerization | Docker / Docker Compose |

---

<a id="structure"></a>
## 📁 4. 프로젝트 구조

기존에는 모든 로직이 `main.py` 한 파일(약 780줄)에 몰려 있었으나, **역할별 모듈로 분리**하여 유지보수성과 가독성을 높였습니다. 파일명만으로 어떤 코드가 들어있는지 바로 알 수 있도록 구성했습니다.

```
upm-server/
├── main.py                    # 앱 진입점 — FastAPI 초기화 · CORS · 라우터 등록 · 서버 실행
├── database.py                # DB 엔진 · 세션(SessionLocal) · get_db · 테이블 생성/마이그레이션(init_db)
├── models.py                  # SQLAlchemy DB 테이블 정의 (4종)
├── schemas.py                 # Pydantic 요청/응답 모델 (데이터 검증)
├── optimizer.py               # 최적화 룰셋 · 화이트리스트/보호목록 · 프로세스 판정 로직
└── routers/                   # 기능별 API 라우터 패키지
    ├── metrics.py             #   텔레메트리 수신 · 상태 · 로그 · 추이 조회
    ├── control.py             #   최적화 · 종료 · 재시작 원격 명령
    ├── optimization.py        #   룰셋 · 프로세스 분석 · 예외 관리 · 종료 이력
    └── dashboard.py           #   Chart.js 기반 실시간 웹 대시보드 HTML
```

| 파일 | 책임 | 주요 내용 |
|------|------|-----------|
| `main.py` | **진입점** | 앱 초기화, `init_db()` 호출, 4개 라우터 `include_router` 등록 |
| `database.py` | **DB 인프라** | 엔진/세션 생성, `get_db` 의존성, `gpuTemp → gpuUsage` 자동 마이그레이션 |
| `models.py` | **테이블 정의** | `TelemetryLog` · `ProcessLog` · `UserException` · `OptimizationHistory` |
| `schemas.py` | **데이터 검증** | `TelemetryData` · `ProcessInfo` · `AnalyzeRequest` · `ExceptionRequest` · `ReportRequest` 등 |
| `optimizer.py` | **최적화 두뇌** | `WHITELIST` · `HARD_PROTECT` · `optimize_rules()` · 서버 자기보호(`_strip_self_kill`) |
| `routers/metrics.py` | **모니터링 API** | `/api/v1/metrics` · `/status` · `/api/v1/logs` · `/api/v1/metrics/history` |
| `routers/control.py` | **제어 API** | `/optimize` · `/shutdown` · `/restart` |
| `routers/optimization.py` | **최적화 API** | `/api/v1/optimization/*` (rules · analyze · exceptions · report · history) |
| `routers/dashboard.py` | **대시보드** | `/dashboard` HTML 페이지 렌더링 |

> 💡 파일을 나눈 뒤에도 **모든 API 경로와 동작은 이전과 100% 동일**합니다. `main.py`가 각 라우터를 `include_router()`로 등록하므로 클라이언트(C# 에이전트·모바일 앱) 측 수정은 필요 없습니다. 서버 실행 방법도 그대로 `python main.py` 입니다.

---

<a id="features"></a>
## 📂 5. 서버 기능 상세

- **실시간 하드웨어 데이터 수집 및 유효성 검증**  
  C# 에이전트로부터 전달받은 부하 수치를 비동기로 영구 적재하고, Pydantic 스키마 필터링으로 비정상 패킷을 차단합니다.

- **글로벌 최적화 룰셋 실시간 배포**  
  서버 내부에 정립된 blackList / whiteList 프로세스 사양을 엔드포인트를 통해 즉각적으로 클라이언트에 반환합니다.

- **실시간 모니터링 대시보드 호스팅**  
  웹 브라우저 기반 관제 환경에 최적화된 실시간 대시보드 UI를 자체 호스팅합니다.

- **SQLAlchemy 2.0 기반 경고 최소화**  
  `MovedIn20Warning` 누수를 원천 차단하여 프로덕션 레벨의 구동 안정성을 확보했습니다.

---

<a id="algorithm"></a>
## 🧠 6. 최적화 알고리즘 (Smart Cleanup)

> 💡 이번 업데이트의 **핵심 변경 사항**입니다. 기존에는 서버가 고정된 화이트/블랙리스트만 배포했지만, 이제 **수집된 실데이터를 분석해 종료 대상을 스스로 판단**하고, **서버 자기 자신·개발 도구·사용자 지정 프로세스는 절대 종료하지 않도록** 다단계 안전장치를 갖췄습니다.

### 🎯 설계 목표

| 목표 | 해결 방법 |
|------|-----------|
| **오탐(誤炭) 방지** | 시스템 필수·개발 도구·사용자 예외 프로세스를 종료 후보에서 원천 차단 |
| **자기 보호** | 서버 자신(`python`/`uvicorn`)이 kill 목록에 오르는 자살 상황을 항상 제거 |
| **똑똑한 판단** | 단순 메모리 크기가 아닌 **창 유무 · CPU 유휴 · 메모리**를 종합해 "진짜 놀고 있는" 프로세스만 정리 |
| **데이터 기반** | 전체 PC에서 자주 잡히는 고메모리 프로세스를 빈도순으로 자동 집계해 글로벌 블랙리스트 생성 |

### ⚙️ 판정 파이프라인 — `POST /api/v1/optimization/analyze`

C# 에이전트가 보낸 실시간 프로세스 목록을 아래 **우선순위 규칙**에 따라 위에서부터 순차 판정하며, 먼저 걸리는 규칙이 최종 결정을 내립니다.

```
┌────────────────────────────────────────────────────────────────┐
│  프로세스 1건 판정 흐름 (위에서부터 우선 적용)                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ① 절대 보호 (HARD_PROTECT)                                     │
│     isSystemCritical == true                                   │
│     OR 개발도구·시스템·셸(python, code, svchost …)             │
│     OR 사용자 예외 목록(machineId별 '종료 금지')              │
│        └──▶  ✅ 보호 (종료 안 함)                               │
│                                                                │
│  ② 고메모리 강제 종료 (FORCE_KILL)                             │
│     memory ≥ 1GB  →  창이 있어도 종료 (게임 등)               │
│        └──▶  🔴 killList 추가                                   │
│                                                                │
│  ③ 똑똑한 정리 (IDLE_KILL) — 3가지 동시 만족                   │
│     창 없음(hasVisibleWindow=false)                           │
│     AND CPU 유휴 (cpuPercent < 1.0%)                           │
│     AND memory ≥ 200MB                                         │
│        └──▶  🔴 killList 추가                                   │
│                                                                │
│  ④ 위 어디에도 안 걸림  →  ✅ 보호 (그대로 둠)                 │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  🛡️ 최종 안전장치: python / pythonw / uvicorn 은 점수와        │
│     무관하게 killList에서 항상 제거 (서버 자기보호)           │
└────────────────────────────────────────────────────────────────┘
```

### 📐 판정 기준 상수

| 상수 | 값 | 의미 |
|------|----|------|
| `FORCE_KILL_MEMORY_BYTES` | 1 GB (1,073,741,824) | 창이 있어도 무조건 종료하는 고메모리 임계값 |
| `IDLE_MEMORY_BYTES` | 200 MB (209,715,200) | 유휴 프로세스로 판단할 최소 점유 메모리 |
| `IDLE_CPU_THRESHOLD` | 1.0 % | 이 값 미만이면 CPU 유휴 상태로 간주 |
| `MEMORY_THRESHOLD_BYTES` | 500 MB (524,288,000) | 글로벌 블랙리스트 후보로 집계할 고메모리 기준 |
| `BLACKLIST_MAX` | 10 | 자동 생성 블랙리스트 최대 개수 |
| `RECENT_WINDOW` | 1 시간 | 블랙리스트 집계 시 참고할 최근 데이터 범위 |

### 📊 데이터 기반 글로벌 블랙리스트 — `GET /api/v1/optimization/rules`

`process_logs` 테이블을 분석하여 **동적으로** 블랙리스트를 생성합니다.

1. 최근 1시간 내 수집된 프로세스만 대상으로 제한
2. `isSystemCritical == false` **AND** `memory ≥ 500MB` 조건 필터링
3. 전체 PC에서의 **등장 빈도(freq) 내림차순** 정렬 → 상위 10개 선정
4. 화이트리스트 프로세스 및 서버 자신(`python`/`uvicorn`)은 제외

### 🔐 다단계 보호 계층

| 계층 | 대상 | 역할 |
|------|------|------|
| `WHITELIST` | svchost, explorer, lsass 등 시스템 필수 | 블랙리스트에서 제외 |
| `HARD_PROTECT` | VS Code, dotnet, git, 셸/터미널 등 개발도구 | 메모리·창과 무관하게 무조건 보호 |
| `UserException` | machineId별 사용자가 직접 지정한 프로세스 | "절대 종료 금지" 개인화 예외 |
| `_ALWAYS_EXCLUDE_FROM_KILL` | python / pythonw / uvicorn | 서버 자기 종료 방지 최종 방어선 |

---

<a id="api"></a>
## 📡 7. API 엔드포인트 명세

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/metrics` | C# 에이전트로부터 실시간 메트릭 및 탑 프로세스 리스트 수신 후 DB 저장 |
| `GET` | `/api/v1/logs` | 시계열 텔레메트리 로그 최신순 조회 (기본 최신 50개) |
| `GET` | `/api/v1/metrics/history` | 모바일 앱용 최근 24개 CPU/RAM/GPU 추이 데이터 |
| `GET` | `/api/v1/optimization/rules` | **데이터 기반 동적** 글로벌 최적화 룰셋(블랙/화이트리스트) 반환 |
| `POST` | `/api/v1/optimization/analyze` | 🧠 실시간 프로세스 목록을 Smart Cleanup 알고리즘으로 판정해 `killList` 반환 |
| `POST` | `/api/v1/optimization/exceptions` | machineId별 '절대 종료 금지' 예외 프로세스 등록/삭제 |
| `GET` | `/api/v1/optimization/exceptions` | machineId별 예외 목록 조회 |
| `POST` | `/api/v1/optimization/report` | 실제로 종료된 프로세스 이력 기록 |
| `GET` | `/api/v1/optimization/history` | 종료 이력 조회 (machineId 필터 지원) |
| `GET` | `/status` `POST` `/optimize` `/shutdown` | 모바일 앱용 최신 상태 조회 및 원격 최적화/종료 명령 |
| `GET` | `/dashboard` | Chart.js 기반 실시간 통합 웹 대시보드 렌더링 |
| `GET` | `/docs` | Swagger UI 기반 API 명세서 및 샌드박스 테스트 환경 |

### 📥 POST `/api/v1/metrics` 요청 예시

```json
{
  "machineId": "PC-DESKTOP-001",
  "cpuUsagePercent": 45.2,
  "ramUsagePercent": 62.8,
  "gpuUsagePercent": 78.5,
  "timestamp": "2026-05-28T14:30:00Z",
  "topProcesses": [
    {
      "processId": 1234,
      "processName": "chrome.exe",
      "memoryWorkingSetBytes": 524288000,
      "isSystemCritical": false
    }
  ]
}
```

---

<a id="database"></a>
## 🗄️ 8. 데이터베이스 구조

### 시계열 로그 테이블 — `telemetry_logs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK, AUTO_INCREMENT | 레코드 고유 일련번호 |
| `machineId` | VARCHAR(50) | NOT NULL, INDEX | 에이전트 PC 식별 호스트네임 |
| `cpuUsage` | FLOAT | NOT NULL | CPU 사용률 (%) |
| `ramUsage` | FLOAT | NOT NULL | 물리 메모리 사용률 (%) |
| `gpuUsage` | FLOAT | NOT NULL | GPU 연산 코어 사용률 (%) |
| `gpuTemp` | FLOAT | NULLABLE | NVML 기반 실시간 GPU 온도 (°C) |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 데이터 적재 타임스탬프 |

### 프로세스 로그 테이블 — `process_logs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT (PK) | 레코드 고유 일련번호 |
| `machineId` | VARCHAR(50) | 에이전트 PC 식별자 |
| `processName` | VARCHAR(255) | 프로세스 이름 |
| `memoryWorkingSetBytes` | BIGINT | 프로세스 점유 메모리 (bytes) |
| `isSystemCritical` | BOOLEAN | 시스템 필수 프로세스 여부 |
| `timestamp` | DATETIME | 수집 시각 |

### 사용자 예외 테이블 — `user_exceptions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT (PK) | 레코드 고유 일련번호 |
| `machineId` | VARCHAR(50), INDEX | 예외를 지정한 PC 식별자 |
| `processName` | VARCHAR(255) | '절대 종료 금지'로 지정된 프로세스 |

### 종료 이력 테이블 — `optimization_history`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT (PK) | 레코드 고유 일련번호 |
| `machineId` | VARCHAR(50), INDEX | 종료가 수행된 PC 식별자 |
| `processName` | VARCHAR(255) | 실제로 종료된 프로세스 |
| `timestamp` | DATETIME | 종료 시각 |

> **DB 자동 초기화**: 서버 구동 시 모든 테이블 존재 여부를 자동 감사하며, 유실된 경우 `Base.metadata.create_all(engine)`으로 동적 스키마를 생성합니다. 기존 `gpuTemp` 컬럼은 `gpuUsage`로 자동 마이그레이션됩니다.

---

<a id="dashboard"></a>
## 📊 9. 실시간 웹 대시보드

`/dashboard` 접속 시 다수 원격 PC 자원을 관제하는 통합 대시보드가 활성화됩니다.

- **실시간 요약 메트릭 카드** — 최신 단말기의 CPU / RAM / GPU 점유율을 컬러 배지와 함께 표시
- **CPU & RAM 트렌드 차트** — Chart.js 기반 시계열 라인 그래프로 리소스 변화 추이 추적
- **GPU 퍼포먼스 면적 차트** — GPU 특수성 모니터링을 위한 Area Line Chart 적용
- **실시간 로그 그리드** — 최신 이력 10개를 10초 주기 비동기 자동 갱신 (브라우저 깜빡임 없음)

---

<a id="installation"></a>
## 🚀 10. 설치 및 배포 가이드

### 💡 방법 A. 로컬 파이썬 가상환경 (Local venv)

로컬 개발 및 개별 테스트 환경에 적합합니다.

**1단계 — 가상환경 생성 및 활성화**

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

**2단계 — 의존성 설치**

```bash
pip install fastapi uvicorn flask sqlalchemy pymysql pydantic cryptography
```

**3단계 — DB 연결 주소 수정**

`main.py` 또는 `database.py` 상단의 접속 주소를 로컬 환경에 맞게 변경합니다.

```python
# 기본 패스워드: admin1234
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:admin1234@localhost:3306/upm_db"
```

**4단계 — 서버 가동**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 🐳 방법 B. Docker Compose 통합 배포 (권장)

Ubuntu Server 또는 라즈베리파이 환경에서 단일 명령으로 DB + 서버를 통합 배포하는 실무형 방식입니다.

**1단계 — DB 연결 주소를 Docker 내부 네트워크로 변경**

```python
# 컨테이너 서비스 이름(db)으로 변경
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@db:3306/upm_db"
```

**2단계 — 빌드 및 백그라운드 배포**

```bash
sudo docker compose up --build -d
```

**3단계 — 컨테이너 상태 확인**

```bash
sudo docker compose ps
```

**4단계 — 인프라 종료**

```bash
sudo docker compose down
```

---

<a id="ngrok"></a>
## 🌐 11. 외부 네트워크 협업 가이드 (ngrok)

팀원이 각자 다른 외부 환경에서 서버에 데이터를 전송하거나 대시보드를 연동할 때 사용합니다.

**1단계 — 인증 토큰 등록 (최초 1회)**

```bash
ngrok config add-authtoken 본인의_고유_인증_토큰_문자열
```

**2단계 — 서버 가동 및 터널 오픈 (터미널 2개)**

```bash
# 터미널 1 — 백엔드 서버 실행
python main.py

# 터미널 2 — 외부 터널링 가동
ngrok http 8000
```

**3단계 — 팀원 공유용 주소 식별**

터널 활성화 후 콘솔에 출력되는 `Forwarding` 주소를 팀원에게 공유합니다.

```
Forwarding  https://abcd-123-456.ngrok-free.app -> http://localhost:8000
```

| 용도 | 주소 |
|------|------|
| C# 에이전트 연동 | `https://abcd-123-456.ngrok-free.app/api/v1/metrics` |
| 대시보드 접속 | `https://abcd-123-456.ngrok-free.app/dashboard` |

> ⚠️ ngrok 재시작 시 포워딩 도메인 주소가 변경됩니다. 주소 갱신 시 클라이언트 측 엔드포인트 URL도 반드시 동기화해야 합니다.

---

## 프로젝트 팀원

| 이름 | 역할 | 비고 |
|:---:|:---:|:---|
| 한준탁 | Server | [@Juntak0131](https://github.com/Juntak0131) |
| 윤재호 | Server | [@joy12341234](https://github.com/joy12341234) |

---

<div align="center">

동양미래대학교 컴퓨터소프트웨어공학과 졸업작품 프로젝트  
**UPM — Universal PC Manager**

</div>
