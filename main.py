from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
# --- DB 관련 라이브러리 ---
from sqlalchemy import create_engine, Column, Integer, BigInteger, Float, String, Boolean, DateTime, desc, func, text, inspect as sa_inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uvicorn
import sys

# Windows 콘솔(cp949)에서 이모지/한글 print가 깨지지 않도록 stdout/stderr을 UTF-8로 재설정
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# [1. DB 설정 및 엔진 생성]
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/upm_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# [2. DB 테이블 정의]
class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    id = Column(Integer, primary_key=True, index=True)
    machineId = Column(String(50))
    cpuUsage = Column(Float)
    ramUsage = Column(Float)
    gpuUsage = Column(Float)
    timestamp = Column(DateTime)

class ProcessLog(Base):
    __tablename__ = "process_logs"
    id = Column(Integer, primary_key=True, index=True)
    machineId = Column(String(50))
    processName = Column(String(255))
    memoryWorkingSetBytes = Column(BigInteger)
    isSystemCritical = Column(Boolean)
    timestamp = Column(DateTime)

class UserException(Base):
    """machineId별 '절대 종료하지 마' 예외 목록 (고클린의 예외처리와 동일 역할)."""
    __tablename__ = "user_exceptions"
    id = Column(Integer, primary_key=True, index=True)
    machineId = Column(String(50), index=True)
    processName = Column(String(255))

class OptimizationHistory(Base):
    """실제로 종료된 프로세스의 이력 (machineId별 종료 기록)."""
    __tablename__ = "optimization_history"
    id = Column(Integer, primary_key=True, index=True)
    machineId = Column(String(50), index=True)
    processName = Column(String(255))
    timestamp = Column(DateTime)

# 서버 실행 시 테이블 자동 생성 + 기존 gpuTemp 컬럼 → gpuUsage 마이그레이션
Base.metadata.create_all(bind=engine)

def migrate_gpu_column():
    try:
        inspector = sa_inspect(engine)
        if inspector.has_table("telemetry_logs"):
            cols = [c["name"] for c in inspector.get_columns("telemetry_logs")]
            with engine.begin() as conn:
                if "gpuTemp" in cols and "gpuUsage" not in cols:
                    conn.execute(text("ALTER TABLE telemetry_logs CHANGE gpuTemp gpuUsage FLOAT"))
                    print("✅ DB 마이그레이션 완료: gpuTemp → gpuUsage")
                elif "gpuUsage" not in cols:
                    conn.execute(text("ALTER TABLE telemetry_logs ADD COLUMN gpuUsage FLOAT"))
                    print("✅ DB 컬럼 추가: gpuUsage")
    except Exception as e:
        print(f"⚠️ DB 마이그레이션 오류: {e}")

migrate_gpu_column()

# [3. DB 세션 관리 함수 (Dependency Injection)]
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# [4. FastAPI 앱 초기화]
app = FastAPI(title="UPM Global Optimization Server", version="3.0")

# --- 모바일 앱 통신 허용 (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# [5. Pydantic 모델 (데이터 검증용)]
class ProcessInfo(BaseModel):
    processId: int
    processName: str
    memoryWorkingSetBytes: int
    isSystemCritical: bool
    hasVisibleWindow: bool = False      # 보이는 창 존재 여부
    cpuPercent: float = 0.0             # 프로세스 CPU 사용률
    isCurrentUserOwned: bool = True     # 현재 사용자 계정 소유 여부

class TelemetryData(BaseModel):
    machineId: str
    cpuUsagePercent: float
    ramUsagePercent: float
    ramUsedGb: float = 0.0       # 모바일 앱용 RAM 실수치
    ramTotalGb: float = 0.0      # 모바일 앱용 RAM 총량
    gpuUsagePercent: Optional[float] = None       # 새 에이전트용
    gpuTemperatureCelsius: Optional[float] = None  # 기존 에이전트 호환용
    timestamp: datetime
    topProcesses: List[ProcessInfo] = []

class TelemetryResponse(BaseModel):
    id: int
    machineId: str
    cpuUsage: float
    ramUsage: float
    gpuUsage: float
    timestamp: datetime

    class Config:
        from_attributes = True

# RAM 실수치 캐시 (DB 스키마 변경 없이 메모리 유지)
_latest_ram_used_gb: float = 0.0
_latest_ram_total_gb: float = 0.0

# [6. API 엔드포인트]

# 6.1. 텔레메트리 데이터 수신 및 DB 저장
@app.post("/api/v1/metrics")
async def receive_metrics(data: TelemetryData, db: Session = Depends(get_db)):
    global _latest_ram_used_gb, _latest_ram_total_gb
    print(f"[{data.timestamp}] 수신 시도: {data.machineId}")
    print(f" C#이 보낸 GPU 온도 원본: {data.gpuTemperatureCelsius} 도")

    _latest_ram_used_gb = data.ramUsedGb
    _latest_ram_total_gb = data.ramTotalGb

    try:
        gpu_value = data.gpuUsagePercent if data.gpuUsagePercent is not None else (data.gpuTemperatureCelsius or 0.0)
        new_log = TelemetryLog(
            machineId=data.machineId,
            cpuUsage=data.cpuUsagePercent,
            ramUsage=data.ramUsagePercent,
            gpuUsage=gpu_value,
            timestamp=data.timestamp
        )
        db.add(new_log)

        # topProcesses 리스트도 함께 저장
        for proc in data.topProcesses:
            db.add(ProcessLog(
                machineId=data.machineId,
                processName=proc.processName,
                memoryWorkingSetBytes=proc.memoryWorkingSetBytes,
                isSystemCritical=proc.isSystemCritical,
                timestamp=data.timestamp
            ))

        db.commit()
        print(f"✅ [{data.machineId}] MySQL 데이터 저장 성공 (프로세스 {len(data.topProcesses)}건 포함)")
        return {"status": "success", "message": "데이터가 DB에 저장되었습니다."}

    except Exception as e:
        db.rollback()
        print(f"❌ DB 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 6.2. 모바일 대시보드용 최신 상태 조회
@app.get("/status")
async def get_status():
    db = SessionLocal()
    try:
        result = db.query(TelemetryLog).order_by(TelemetryLog.timestamp.desc()).first()
        if result:
            return {
                "cpu": result.cpuUsage,
                "ram": result.ramUsage,
                "gpu": result.gpuUsage,
                "gpuTemp": 0,
                "ram_used": _latest_ram_used_gb,
                "ram_total": _latest_ram_total_gb,
            }
        return {"cpu": 0, "ram": 0, "gpu": 0, "gpuTemp": 0, "ram_used": 0, "ram_total": 0}
    finally:
        db.close()

# 6.3. 모바일 앱 빠른 최적화 명령 처리
@app.post("/optimize")
async def optimize_system():
    try:
        print(" [명령 수신] 스마트폰 앱으로부터 시스템 최적화 명령을 받았습니다!")
        # 실제 최적화 로직 예시
        # import os
        # os.system("명령어")
        return {"status": "success", "message": "Optimization completed"}
    except Exception as e:
        print(f"❌ 최적화 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="최적화 명령 수행 실패")

# 6.4. 모바일 앱 PC 종료 명령 처리
@app.post("/shutdown")
async def shutdown():
    # import os
    # os.system("shutdown /s /t 1") # 실제 테스트 때 주석 해제
    print(" PC 종료 명령 수신 완료")
    return {"status": "success", "message": "PC 종료 명령을 실행합니다."}

# 6.5. 텔레메트리 데이터 조회 (웹 대시보드용)
@app.get("/api/v1/logs", response_model=List[TelemetryResponse])
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(TelemetryLog).order_by(desc(TelemetryLog.timestamp)).limit(limit).all()
    return logs

# 6.6. 모바일 앱용 최근 24개 추이 데이터
@app.get("/api/v1/metrics/history")
async def get_metrics_history():
    db = SessionLocal()
    try:
        logs = db.query(TelemetryLog).order_by(TelemetryLog.timestamp.desc()).limit(24).all()
        logs.reverse()  # 과거 → 현재 순으로 정렬
        history_data = []
        for log in logs:
            time_str = log.timestamp.strftime("%H:%M") if log.timestamp else ""
            history_data.append({
                "time": time_str,
                "cpu": log.cpuUsage,
                "ram": log.ramUsage,
                "gpu": log.gpuUsage if log.gpuUsage else 0.0
            })
        return history_data
    finally:
        db.close()

# 6.7. 글로벌 최적화 룰셋 반환 (DB 기반 동적 생성)

# 종료 대상 판단 기준 상수
MEMORY_THRESHOLD_BYTES = 524288000        # 500MB 이상이면 고메모리 프로세스로 간주
RECENT_WINDOW = timedelta(hours=1)        # 최근 수집 기준 시간 창
BLACKLIST_MAX = 10                        # 블랙리스트 최대 개수

# 절대 종료하면 안 되는 시스템 필수 프로세스 (소문자 / 확장자 제외 기준)
WHITELIST = [
    "svchost", "explorer", "System", "csrss", "lsass", "winlogon",
    # 개발·런타임 관련 프로세스
    "python", "pythonw", "uvicorn", "node", "dotnet", "msbuild",
    "code", "devenv", "servicehub", "cmd", "powershell", "pwsh",
    "windowsterminal", "conhost", "git", "ssh",
]
_WHITELIST_SET = {name.lower() for name in WHITELIST}

# 절대 보호 목록: 창 유무·메모리와 무관하게 무조건 killList에서 제외 (소문자 / 확장자 제외 기준)
HARD_PROTECT = [
    # [VS Code / Visual Studio 관련]
    "code", "devenv", "msbuild", "servicehub", "vbcscompiler", "perfwatson2",
    # [파이썬/서버 런타임]
    "python", "pythonw", "uvicorn", "node", "dotnet",
    # [셸/터미널]
    "cmd", "powershell", "pwsh", "conhost", "windowsterminal", "git",
    # [시스템 필수] 기존 WHITELIST 항목 전부 포함
    *WHITELIST,
]
_HARD_PROTECT_SET = {name.lower() for name in HARD_PROTECT}

# 메모리가 이 값 이상이면 창이 있어도 강제 종료 (고메모리, 게임 등)
FORCE_KILL_MEMORY_BYTES = 1073741824      # 1GB

# "똑똑한 정리" 기준: 백그라운드·유휴 상태로 이 메모리 이상을 점유하면 종료 대상
IDLE_MEMORY_BYTES = 209715200             # 200MB
IDLE_CPU_THRESHOLD = 1.0                  # CPU 사용률이 이 값 미만이면 유휴

# killList에서 점수와 무관하게 항상 제거해야 하는 프로세스.
# 이 서버 자체가 python 프로세스라, killList에 들어가면 서버가 자기 자신을 종료하게 된다.
_ALWAYS_EXCLUDE_FROM_KILL = {"python", "pythonw", "uvicorn"}


def _strip_self_kill(kill_list: list) -> list:
    """killList에서 서버 자신을 죽일 수 있는 프로세스(python/pythonw/uvicorn)를 항상 제거한다."""
    return [name for name in kill_list if _normalize_name(name) not in _ALWAYS_EXCLUDE_FROM_KILL]


def _normalize_name(name: str) -> str:
    """프로세스 이름을 소문자로 정규화하고 .exe 확장자를 제거한다."""
    n = (name or "").strip().lower()
    if n.endswith(".exe"):
        n = n[:-4]
    return n


def optimize_rules(db: Session) -> dict:
    """process_logs를 분석해 동적으로 최적화 룰셋(블랙/화이트리스트)을 생성한다."""
    # 1. 최근 수집된 프로세스 기준 시점 확인
    latest_ts = db.query(func.max(ProcessLog.timestamp)).scalar()

    # 2. 블랙리스트 후보 집계
    #    - isSystemCritical == False
    #    - memoryWorkingSetBytes >= 500MB
    #    - 전체 PC에서 등장 빈도(freq)가 높은 순서
    query = db.query(
        ProcessLog.processName,
        func.count(ProcessLog.id).label("freq"),
    ).filter(
        ProcessLog.isSystemCritical == False,  # noqa: E712 (SQLAlchemy 컬럼 비교)
        ProcessLog.memoryWorkingSetBytes >= MEMORY_THRESHOLD_BYTES,
    )

    # "최근 수집된" 데이터만 대상으로 제한
    if latest_ts is not None:
        query = query.filter(ProcessLog.timestamp >= latest_ts - RECENT_WINDOW)

    rows = query.group_by(ProcessLog.processName).order_by(desc("freq")).all()

    # 3. 화이트리스트에 해당하는 프로세스는 블랙리스트에서 제외
    black_list = []
    for name, _freq in rows:
        if not name or _normalize_name(name) in _WHITELIST_SET:
            continue
        black_list.append(name)
        if len(black_list) >= BLACKLIST_MAX:
            break

    # 안전장치: 점수/빈도와 무관하게 python/pythonw/uvicorn은 killList에서 항상 제거
    black_list = _strip_self_kill(black_list)

    # 4. 결과 반환
    return {
        "version": "v2.0.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "blackList": black_list,
        "whiteList": WHITELIST,
    }


@app.get("/api/v1/optimization/rules")
async def get_optimization_rules(db: Session = Depends(get_db)):
    return optimize_rules(db)


# 6.7-b. 실시간 프로세스 분석 (C# 에이전트가 보낸 프로세스를 즉시 종료 대상으로 변환)
class AnalyzeRequest(BaseModel):
    machineId: str
    topProcesses: List[ProcessInfo] = []


@app.post("/api/v1/optimization/analyze")
async def analyze_processes(req: AnalyzeRequest, db: Session = Depends(get_db)):
    # "똑똑한 정리" 판정 순서 (위에서부터 먼저 걸리는 규칙이 우선)
    #  1) 절대 보호: isSystemCritical 또는 HARD_PROTECT/사용자 예외 → 무조건 제외
    #  2) 고메모리 강제 종료: memory >= FORCE_KILL_MEMORY_BYTES(1GB) → 창 있어도 종료
    #  3) 똑똑한 정리: 창 없음 + CPU 유휴 + memory >= IDLE_MEMORY_BYTES(200MB) 동시 만족 → 종료
    #  4) 그 외 → 보호(그대로 둠)

    # 해당 machineId의 사용자 예외 목록(절대 종료 금지)을 정규화하여 조회
    exception_set = {
        _normalize_name(row.processName)
        for row in db.query(UserException.processName)
        .filter(UserException.machineId == req.machineId)
        .all()
    }

    kill_list = []
    for proc in req.topProcesses:
        norm_name = _normalize_name(proc.processName)
        mem_bytes = proc.memoryWorkingSetBytes
        mem_mb = mem_bytes / (1024 * 1024)

        def _log(verdict: str) -> None:
            print(
                f"🔎 [{req.machineId}] {proc.processName} | "
                f"창={'O' if proc.hasVisibleWindow else 'X'} | "
                f"CPU={proc.cpuPercent:.1f}% | mem={mem_mb:.0f}MB | 판정={verdict}"
            )

        # 1) [절대 보호] 시스템 필수이거나 HARD_PROTECT 목록이면 무조건 제외
        if proc.isSystemCritical or norm_name in _HARD_PROTECT_SET:
            _log("HARD_PROTECT")
            continue
        # (사용자 예외 목록도 절대 보호로 취급 — 사용자가 명시적으로 '종료 금지'한 프로세스)
        if norm_name in exception_set:
            _log("보호(사용자 예외 목록)")
            continue

        # 2) [고메모리 강제 종료] 1GB 이상이면 창이 있어도 종료 (게임 등)
        if mem_bytes >= FORCE_KILL_MEMORY_BYTES:
            _log("FORCE_KILL")
            kill_list.append(proc.processName)
            continue

        # 3) [똑똑한 정리] 창 없음 + CPU 유휴 + 메모리 200MB 이상을 동시 만족하면 종료
        if (
            not proc.hasVisibleWindow
            and proc.cpuPercent < IDLE_CPU_THRESHOLD
            and mem_bytes >= IDLE_MEMORY_BYTES
        ):
            _log("IDLE_KILL")
            kill_list.append(proc.processName)
            continue

        # 4) 위 어디에도 안 걸리면 보호 (그대로 둠)
        _log("보호")

    # 안전장치: 점수와 무관하게 python/pythonw/uvicorn은 killList에서 항상 제거
    # (이 서버 자체가 python 프로세스라 자기 자신을 종료하는 것을 방지)
    kill_list = _strip_self_kill(kill_list)

    print(f"🔍 [{req.machineId}] 분석 완료: 종료 대상 {len(kill_list)}건 → {kill_list}")
    return {"killList": kill_list}


# 6.7-c. 사용자 예외 목록 관리 (machineId별 '절대 종료 금지' 프로세스)
class ExceptionRequest(BaseModel):
    machineId: str
    processName: str
    action: str = "add"   # "add" = 예외 등록, "remove" = 예외 삭제


@app.post("/api/v1/optimization/exceptions")
async def manage_exception(req: ExceptionRequest, db: Session = Depends(get_db)):
    action = (req.action or "add").strip().lower()
    if action not in ("add", "remove"):
        raise HTTPException(status_code=400, detail="action은 'add' 또는 'remove'만 허용됩니다.")

    norm_name = _normalize_name(req.processName)
    if not norm_name:
        raise HTTPException(status_code=400, detail="processName은 비어 있을 수 없습니다.")

    # 대상 machineId + 프로세스의 기존 예외 항목 조회 (이름은 정규화 기준으로 비교)
    existing = [
        row
        for row in db.query(UserException)
        .filter(UserException.machineId == req.machineId)
        .all()
        if _normalize_name(row.processName) == norm_name
    ]

    if action == "add":
        if existing:
            print(f"ℹ️  [{req.machineId}] 예외 이미 존재: {req.processName}")
        else:
            db.add(UserException(machineId=req.machineId, processName=req.processName))
            db.commit()
            print(f"➕ [{req.machineId}] 예외 등록: {req.processName}")
    else:  # remove
        for row in existing:
            db.delete(row)
        db.commit()
        print(f"➖ [{req.machineId}] 예외 삭제: {req.processName} ({len(existing)}건)")

    # 갱신된 해당 머신의 전체 예외 목록 반환
    exceptions = [
        row.processName
        for row in db.query(UserException.processName)
        .filter(UserException.machineId == req.machineId)
        .all()
    ]
    return {"machineId": req.machineId, "exceptions": exceptions}


@app.get("/api/v1/optimization/exceptions")
async def list_exceptions(machineId: str, db: Session = Depends(get_db)):
    exceptions = [
        row.processName
        for row in db.query(UserException.processName)
        .filter(UserException.machineId == machineId)
        .all()
    ]
    return {"machineId": machineId, "exceptions": exceptions}


# 6.7-d. 종료 이력 기록/조회 (실제로 종료된 프로세스를 별도로 기록)
class ReportRequest(BaseModel):
    machineId: str
    killedProcesses: List[str] = []


@app.post("/api/v1/optimization/report")
async def report_optimization(req: ReportRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    count = 0
    for name in req.killedProcesses:
        if not name:
            continue
        db.add(OptimizationHistory(
            machineId=req.machineId,
            processName=name,
            timestamp=now,
        ))
        count += 1
    db.commit()
    print(f"📝 [{req.machineId}] 종료 이력 {count}건 기록")
    return {"status": "success", "machineId": req.machineId, "recorded": count}


@app.get("/api/v1/optimization/history")
async def get_optimization_history(
    machineId: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(OptimizationHistory)
    if machineId:
        query = query.filter(OptimizationHistory.machineId == machineId)
    rows = query.order_by(desc(OptimizationHistory.timestamp)).limit(limit).all()
    return [
        {
            "machineId": row.machineId,
            "processName": row.processName,
            "timestamp": row.timestamp,
        }
        for row in rows
    ]


# 6.8. 대시보드 페이지 (개선된 UI)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UPM Global Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f46e5;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 0;
        }
        .navbar {
            background: var(--card-bg);
            padding: 1rem 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .navbar h1 { font-size: 1.25rem; margin: 0; color: var(--primary); }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        .card-title { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem; font-weight: 600; }
        .card-value { font-size: 1.875rem; font-weight: 700; color: var(--text-main); }
        .card-sub { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem; }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .table-container {
            background: var(--card-bg);
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: #f1f5f9; padding: 1rem; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); }
        td { padding: 1rem; border-top: 1px solid #e2e8f0; font-size: 0.875rem; }
        tr:hover { background-color: #f8fafc; }
        .badge {
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-cpu { background: #fee2e2; color: #b91c1c; }
        .badge-ram { background: #dbeafe; color: #1d4ed8; }
        .badge-gpu { background: #fef3c7; color: #92400e; }
        .refresh-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.9; }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>UPM Global Control Center</h1>
        <div>
            <span id="lastUpdate" style="font-size: 0.875rem; color: var(--text-muted); margin-right: 1rem;"></span>
            <button class="refresh-btn" onclick="fetchData()">새로고침</button>
        </div>
    </div>

    <div class="container">
        <div class="summary-grid">
            <div class="card">
                <div class="card-title">LATEST CPU USAGE</div>
                <div class="card-value" id="curCpu">0%</div>
                <div class="card-sub" id="curCpuId">-</div>
            </div>
            <div class="card">
                <div class="card-title">LATEST RAM USAGE</div>
                <div class="card-value" id="curRam">0%</div>
                <div class="card-sub" id="curRamId">-</div>
            </div>
            <div class="card">
                <div class="card-title">LATEST GPU USAGE</div>
                <div class="card-value" id="curGpu">0%</div>
                <div class="card-sub" id="curGpuId">-</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="card">
                <div class="card-title">RESOURCE TRENDS (CPU & RAM)</div>
                <canvas id="mainChart" height="200"></canvas>
            </div>
            <div class="card">
                <div class="card-title">GPU USAGE TREND (%)</div>
                <canvas id="gpuChart" height="200"></canvas>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Machine ID</th>
                        <th>CPU</th>
                        <th>RAM</th>
                        <th>GPU Usage</th>
                    </tr>
                </thead>
                <tbody id="logTableBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        let mainChart, gpuChart;

        async function fetchData() {
            try {
                const response = await fetch('/api/v1/logs?limit=30');
                const data = await response.json();
                if (data.length > 0) {
                    updateSummary(data[0]);
                    updateTable(data);
                    updateCharts(data);
                    document.getElementById('lastUpdate').innerText = 'Last updated: ' + new Date().toLocaleTimeString();
                }
            } catch (e) {
                console.error("Fetch error:", e);
            }
        }

        function updateSummary(latest) {
            document.getElementById('curCpu').innerText = latest.cpuUsage.toFixed(1) + '%';
            document.getElementById('curCpuId').innerText = latest.machineId;
            document.getElementById('curRam').innerText = latest.ramUsage.toFixed(1) + '%';
            document.getElementById('curRamId').innerText = latest.machineId;
            document.getElementById('curGpu').innerText = latest.gpuUsage.toFixed(1) + '%';
            document.getElementById('curGpuId').innerText = latest.machineId;
        }

        function updateTable(data) {
            const tbody = document.getElementById('logTableBody');
            tbody.innerHTML = '';
            data.slice(0, 10).forEach(log => {
                const row = `<tr>
                    <td>${new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td><strong>${log.machineId}</strong></td>
                    <td><span class="badge badge-cpu">${log.cpuUsage.toFixed(1)}%</span></td>
                    <td><span class="badge badge-ram">${log.ramUsage.toFixed(1)}%</span></td>
                    <td><span class="badge badge-gpu">${log.gpuUsage.toFixed(1)}%</span></td>
                </tr>`;
                tbody.innerHTML += row;
            });
        }

        function updateCharts(data) {
            const rev = [...data].reverse();
            const labels = rev.map(l => new Date(l.timestamp).toLocaleTimeString());

            if (mainChart) mainChart.destroy();
            if (gpuChart) gpuChart.destroy();

            const ctxMain = document.getElementById('mainChart').getContext('2d');
            mainChart = new Chart(ctxMain, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'CPU (%)', data: rev.map(l => l.cpuUsage), borderColor: '#ef4444', tension: 0.3, fill: false },
                        { label: 'RAM (%)', data: rev.map(l => l.ramUsage), borderColor: '#3b82f6', tension: 0.3, fill: false }
                    ]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });

            const ctxGpu = document.getElementById('gpuChart').getContext('2d');
            gpuChart = new Chart(ctxGpu, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{ label: 'GPU Usage (%)', data: rev.map(l => l.gpuUsage), borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', tension: 0.3, fill: true }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        }

        fetchData();
        setInterval(fetchData, 10000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# [7. 서버 실행]
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)