# UPM Global Server

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)

**동양미래대학교 컴퓨터소프트웨어공학과 졸업작품**  
PC 하드웨어 모니터링 및 원격 최적화 시스템 — **서버 파트**

</div>

---

## 목차

1. [프로젝트 개요](#-1-프로젝트-개요)
2. [시스템 아키텍처](#-2-시스템-아키텍처)
3. [서버의 역할 (기능 상세)](#-3-서버의-역할-기능-상세)
4. [API 엔드포인트](#-4-api-엔드포인트)
5. [데이터베이스 구조](#-5-데이터베이스-구조)
6. [대시보드](#-6-대시보드)
7. [설치 및 실행](#-7-설치-및-실행)
8. [서버 접속 방법 (ngrok)](#-8-서버-접속-방법-ngrok)

---

## 1. 프로젝트 개요

**UPM (Universal PC Master)** 은 여러 대의 PC 하드웨어 상태를 중앙에서 실시간으로 모니터링하고, 글로벌 최적화 룰셋을 배포하는 시스템입니다.

이 레포지토리는 그 시스템의 **중앙 서버(Tier 2)** 를 담당합니다.

| 구분 | 설명 |
|------|------|
| 역할 | C# 에이전트로부터 하드웨어 데이터 수집 · 저장 · 제공 |
| 언어 | Python 3.10+ |
| 프레임워크 | FastAPI (비동기 REST API) |
| 데이터베이스 | MySQL 8.0 (SQLAlchemy ORM) |
| 외부 접속 | ngrok 터널링 지원 |

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        UPM 전체 시스템                           │
│                                                                  │
│  ┌──────────────┐   HTTP POST    ┌──────────────────────────┐   │
│  │  PC Agent    │ ─────────────► │   UPM Global Server      │   │
│  │  (C# / WPF)  │                │   (Python / FastAPI)     │   │
│  │              │                │                          │   │
│  │  ▸ CPU 사용률│   HTTP GET     │  ┌────────────────────┐  │   │
│  │  ▸ RAM 사용률│ ◄───────────── │  │   MySQL Database   │  │   │
│  │  ▸ GPU 사용률│  최적화 룰셋   │  │  (telemetry_logs)  │  │   │
│  └──────────────┘                │  └────────────────────┘  │   │
│                                  │                          │   │
│  ┌──────────────┐   HTTP GET     │  ┌────────────────────┐  │   │
│  │   Browser    │ ─────────────► │  │  Web Dashboard     │  │   │
│  │  (관리자)    │                │  │  (HTML / Chart.js) │  │   │
│  └──────────────┘                │  └────────────────────┘  │   │
│                                  └──────────────────────────┘   │
│                                                                  │
│   ── 로컬망(LAN) ──────────────────────────────────────────      │
│   ── 외부망(ngrok 터널) ───────────────────────────────────      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 서버의 역할 (기능 상세)

### 실시간 하드웨어 데이터 수집
C# 에이전트가 주기적으로 서버에 `POST` 요청을 보내면, 서버는 해당 데이터를 수신하여 MySQL DB에 저장합니다.  
수집 항목: **CPU 사용률(%)**, **RAM 사용률(%)**, **GPU 사용률(%)**

### 글로벌 최적화 룰셋 배포
서버가 관리하는 `blackList` / `whiteList` 프로세스 목록을 에이전트에게 제공합니다.  
에이전트는 이 룰을 기반으로 불필요한 프로세스를 자동으로 처리합니다.

### 실시간 모니터링 대시보드
웹 브라우저에서 `/dashboard` 에 접속하면 모든 PC의 리소스 상태를 한눈에 볼 수 있는 대시보드를 제공합니다.  
Chart.js 기반 라인 차트로 시간 흐름에 따른 CPU/RAM/GPU 사용률을 시각화합니다.

### 데이터 조회 API
저장된 로그를 최신순으로 조회할 수 있는 REST API를 제공합니다. 프론트엔드 및 관리 도구와 연동 가능합니다.

---

## 4. API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/metrics` | C# 에이전트로부터 하드웨어 데이터를 수신하고 DB에 저장 |
| `GET` | `/api/v1/logs` | DB에 저장된 텔레메트리 로그 조회 (최신순, 기본 50개) |
| `GET` | `/api/v1/optimization/rules` | 글로벌 최적화 룰셋(블랙리스트/화이트리스트) 반환 |
| `GET` | `/dashboard` | 실시간 웹 모니터링 대시보드 |
| `GET` | `/docs` | FastAPI 자동 생성 API 문서 (Swagger UI) |

### POST `/api/v1/metrics` 요청 예시

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

## 5. 데이터베이스 구조

### 테이블: `telemetry_logs`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INT (PK) | 자동 증가 고유 ID |
| `machineId` | VARCHAR(50) | PC 고유 식별자 |
| `cpuUsage` | FLOAT | CPU 사용률 (%) |
| `ramUsage` | FLOAT | RAM 사용률 (%) |
| `gpuUsage` | FLOAT | GPU 사용률 (%) |
| `timestamp` | DATETIME | 데이터 수집 시각 |

> 서버 실행 시 테이블이 없으면 **자동으로 생성**됩니다 (`Base.metadata.create_all`).

---

## 6. 대시보드

`/dashboard` 경로에 브라우저로 접속하면 아래와 같은 실시간 모니터링 화면을 볼 수 있습니다.

- **요약 카드**: 가장 최근에 수신된 CPU / RAM / GPU 사용률을 한눈에 표시
- **CPU & RAM 트렌드 차트**: 시간 흐름에 따른 CPU·RAM 사용률 추이 (라인 차트)
- **GPU 사용률 차트**: GPU 사용률 추이 (면적 라인 차트)
- **로그 테이블**: 최근 10개 로그를 실시간으로 표시 (10초마다 자동 갱신)

---

## 7. 설치 및 실행

### 사전 준비

- Python 3.10 이상
- MySQL 8.0 실행 중 + `upm_db` 데이터베이스 생성

```sql
CREATE DATABASE upm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 패키지 설치

```bash
pip install fastapi uvicorn sqlalchemy pymysql pydantic
```

### DB 연결 정보 설정

`main.py` 상단의 연결 문자열을 본인 환경에 맞게 수정합니다.

```python
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:비밀번호@localhost:3306/upm_db"
```

### 서버 실행

```bash
python main.py
```

서버가 정상 실행되면 아래 주소로 접속 가능합니다.

| 주소 | 설명 |
|------|------|
| `http://localhost:8000/docs` | Swagger API 문서 |
| `http://localhost:8000/dashboard` | 모니터링 대시보드 |

---

## 8. 서버 접속 방법 (ngrok)

팀원이 각자 다른 장소(집, 학교 등)에서 접속할 때 사용합니다.

**① ngrok 설정 (최초 1회)**

1. [ngrok.com](https://ngrok.com) 회원가입 후 Authtoken 복사
2. 터미널에 입력:

```bash
ngrok config add-authtoken 여기에_토큰_붙여넣기
```

**② 서버 실행 후 터널 오픈**

터미널 창 2개를 엽니다.

```bash
# 터미널 1: 서버 실행
python main.py

# 터미널 2: ngrok 터널 오픈
ngrok http 8000
```

**③ 팀원에게 주소 공유**

ngrok 실행 화면에서 `Forwarding` 항목의 주소를 복사합니다.

```
Forwarding   https://abcd-123-456.ngrok-free.app -> http://localhost:8000
```

팀원 접속 주소:

```
https://abcd-123-456.ngrok-free.app/dashboard       ← 대시보드
https://abcd-123-456.ngrok-free.app/api/v1/metrics  ← 데이터 수신
```

> **주의**: ngrok을 재실행하면 주소가 바뀝니다. 주소가 바뀔 때마다 팀원에게 재공유하세요.

---

<div align="center">

동양미래대학교 컴퓨터소프트웨어공학과  
졸업작품 프로젝트 — UPM (Universal PC Master)

</div>
