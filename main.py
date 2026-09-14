"""UPM Global Optimization Server - 앱 진입점.

- FastAPI 앱 초기화 및 CORS 설정
- DB 테이블 생성/마이그레이션(init_db)
- 각 기능별 라우터 등록
- 서버 실행(uvicorn)

실제 로직은 아래 모듈에 나누어져 있습니다:
    database.py            : DB 엔진/세션/마이그레이션
    models.py              : DB 테이블 정의
    schemas.py             : Pydantic 요청/응답 모델
    optimizer.py           : 최적화 룰셋/판정 로직
    routers/metrics.py     : 텔레메트리 수신/상태/로그/추이
    routers/control.py     : 최적화/종료/재시작 명령
    routers/optimization.py: 룰셋/분석/예외/이력 API
    routers/dashboard.py   : 웹 대시보드 페이지
    routers/admin.py       : 관리자 웹사이트용 API (세션 인증 필요)
    routers/auth_web.py    : 관리자 웹 로그인(세션 쿠키)
"""

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Windows 콘솔(cp949)에서 이모지/한글 print가 깨지지 않도록 stdout/stderr을 UTF-8로 재설정
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from database import init_db
from routers import metrics, control, optimization, dashboard, admin, auth_web

# 서버 실행 시 테이블 자동 생성 + gpuTemp → gpuUsage 마이그레이션
init_db()

# [FastAPI 앱 초기화]
app = FastAPI(title="UPM Global Optimization Server", version="3.0")

# --- 모바일 앱 통신 허용 (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# [라우터 등록]
app.include_router(metrics.router)
app.include_router(control.router)
app.include_router(optimization.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(auth_web.router)


# [서버 실행]
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
