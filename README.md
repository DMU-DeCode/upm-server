# UPM_Server
# 🖥️ UPM (Universal PC Master) - Global Server

UPM 프로젝트의 중앙 통제실 역할을 하는 **Python FastAPI 기반 백엔드 서버**입니다. 데스크톱 에이전트(C#)로부터 실시간 하드웨어 데이터를 수집하고, 이를 분석하여 최적화 룰셋을 제공하며 모든 기록을 MySQL 데이터베이스에 영구 저장합니다.

---

## 📝 1. 프로젝트 개요 (Summary)

* **데스크톱 리소스 모니터링**: C# 에이전트가 수집한 CPU, RAM, GPU 수치를 실시간으로 수신합니다.
* **데이터 영구 보관**: 수집된 모든 하드웨어 텔레메트리를 MySQL(MariaDB)에 저장하여 통계 분석의 기초 자료로 활용합니다.
* **비동기 고성능 아키텍처**: FastAPI의 비동기(Async) 처리를 통해 다수의 에이전트로부터 오는 데이터를 지연 없이 처리합니다.

---

## 🛠️ 2. 기술 스택 (Tech Stack)

* **Language**: Python 3.10+
* **Framework**: FastAPI
* **Database**: MySQL 
* **Communication**: REST API (HTTP POST/GET)

---

## 📂 3. 주요 서버 코드 설명

서버는 크게 두 개의 핵심 엔드포인트(Endpoint)를 제공합니다.

| 경로 (Endpoint) | 방식 | 역할 |
| :--- | :---: | :--- |
| `/api/v1/specs` | `POST` | 하드웨어 상세 사양(CPU명, 코어 수 등)을 수신하여 기기를 등록합니다. |
| `/api/v1/status` | `POST` | 실시간 점유율(CPU%, RAM%, GPU Temp) 데이터를 수신하고 DB에 저장합니다. |

---

## 🚀 4. 설치 및 실행 방법 (Installation)

### 1) 필수 패키지 설치
터미널에서 아래 명령어를 입력하여 필요한 라이브러리를 다운로드합니다.
```bash
pip install fastapi uvicorn pydantic mysql-connector-python
```

### 2) 서버 실행
개인 PC 연동 테스트를 위해 외부 접속이 가능하도록 호스트를 0.0.0.0으로 설정합니다.
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

# 🛠️ UPM Server - 개인 작업 및 학습 브랜치 (JHPractice)

이 브랜치는 **Dongyang Mirae University 컴퓨터소프트웨어공학과** 졸업 작품인 'PC 하드웨어 모니터링 및 원격 제어 시스템'의 **서버 인프라(Tier 2)**를 개발하고 테스트하는 공간입니다.

## 📌 이번 브랜치 작업 목표
1. **FastAPI**를 활용한 데이터 수집 서버 구축
2. **MySQL** 데이터베이스 연동 및 데이터 영구 저장 로직 구현

---

## 🏗️ 시스템 아키텍처 (담당 부분)
- **Framework**: FastAPI (Python)
- **Database**: MySQL 8.0

---

## 🚀 설치 및 실행 방법 (How to Run)

### 1. 가상환경 및 필수 라이브러리 설치
```bash
pip install fastapi uvicorn sqlalchemy pymysql
