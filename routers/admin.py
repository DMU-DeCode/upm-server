"""관리자 웹사이트용 API (읽기 전용, 전 엔드포인트 관리자 인증 필요).

- GET /api/v1/admin/machines              : 등록된 PC 목록(머신별 최신 상태 + 온라인 여부)
- GET /api/v1/admin/machines/{machine_id} : 특정 PC 상세(텔레메트리/종료이력/예외목록)
- GET /api/v1/admin/summary               : 전체 요약(총/온라인 PC 수, 평균 사용률, 오늘 종료건수)

인증: 세션 쿠키 기반(require_admin_session). 미인증 시 /login으로 리다이렉트한다.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from database import get_db
from models import TelemetryLog, OptimizationHistory, UserException
from routers.auth_web import require_admin_session

# 온라인 판정 기준: 최근 수신이 5분 이내면 online
ONLINE_WINDOW = timedelta(minutes=5)


# 라우터 레벨 의존성으로 3개 엔드포인트 전부 세션 인증
router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(require_admin_session)])


def _latest_per_machine(db: Session):
    """머신별 최신 텔레메트리 1건씩 반환한다(machineId 기준 dedupe)."""
    # 머신별 최신 timestamp 서브쿼리 → 원본 테이블과 self-join
    subq = (
        db.query(
            TelemetryLog.machineId,
            func.max(TelemetryLog.timestamp).label("last"),
        )
        .group_by(TelemetryLog.machineId)
        .subquery()
    )
    rows = (
        db.query(TelemetryLog)
        .join(
            subq,
            and_(
                TelemetryLog.machineId == subq.c.machineId,
                TelemetryLog.timestamp == subq.c.last,
            ),
        )
        .all()
    )
    # 동일 timestamp 중복행이 있으면 machineId당 1건만 유지
    latest = {}
    for row in rows:
        if row.machineId not in latest:
            latest[row.machineId] = row
    return list(latest.values())


# 등록된 PC 목록 (머신별 최신 상태 + 온라인 여부)
@router.get("/machines")
async def list_machines(db: Session = Depends(get_db)):
    # 온라인 판정은 서버 로컬 시각 기준(naive). 텔레메트리 timestamp는 에이전트 payload 값이며
    # MySQL DATETIME(naive)로 저장되므로 datetime.now()와 직접 비교한다.
    cutoff = datetime.now() - ONLINE_WINDOW
    machines = []
    for row in _latest_per_machine(db):
        machines.append({
            "machineId": row.machineId,
            "lastSeen": row.timestamp,
            "cpuUsage": row.cpuUsage,
            "ramUsage": row.ramUsage,
            "gpuUsage": row.gpuUsage,
            "online": bool(row.timestamp and row.timestamp >= cutoff),
        })
    # 온라인 우선 + machineId 순으로 정렬
    machines.sort(key=lambda m: (not m["online"], m["machineId"]))
    return machines


# 특정 PC 상세 (텔레메트리 / 종료 이력 / 예외 목록)
@router.get("/machines/{machine_id}")
async def get_machine_detail(
    machine_id: str = Path(..., max_length=50, pattern=r"^[A-Za-z0-9_-]+$"),
    telemetry_limit: int = Query(24, ge=1, le=100),
    history_limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    telemetry = (
        db.query(TelemetryLog)
        .filter(TelemetryLog.machineId == machine_id)
        .order_by(desc(TelemetryLog.timestamp))
        .limit(telemetry_limit)
        .all()
    )
    # 텔레메트리가 한 건도 없으면 존재하지 않는 PC로 간주
    if not telemetry:
        raise HTTPException(status_code=404, detail=f"'{machine_id}' 머신을 찾을 수 없습니다.")

    history = (
        db.query(OptimizationHistory)
        .filter(OptimizationHistory.machineId == machine_id)
        .order_by(desc(OptimizationHistory.timestamp))
        .limit(history_limit)
        .all()
    )
    exceptions = [
        row.processName
        for row in db.query(UserException.processName)
        .filter(UserException.machineId == machine_id)
        .all()
    ]

    return {
        "machineId": machine_id,
        "telemetry": [
            {
                "id": t.id,
                "cpuUsage": t.cpuUsage,
                "ramUsage": t.ramUsage,
                "gpuUsage": t.gpuUsage,
                "timestamp": t.timestamp,
            }
            for t in telemetry
        ],
        "optimizationHistory": [
            {
                "processName": h.processName,
                "timestamp": h.timestamp,
            }
            for h in history
        ],
        "exceptions": exceptions,
    }


# 전체 요약 (총/온라인 PC 수, 평균 사용률, 오늘 종료 건수)
@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    latest = _latest_per_machine(db)
    cutoff = datetime.now() - ONLINE_WINDOW

    total_machines = len(latest)
    online_machines = sum(
        1 for row in latest if row.timestamp and row.timestamp >= cutoff
    )
    if total_machines:
        avg_cpu = sum(row.cpuUsage or 0.0 for row in latest) / total_machines
        avg_ram = sum(row.ramUsage or 0.0 for row in latest) / total_machines
    else:
        avg_cpu = 0.0
        avg_ram = 0.0

    # optimization_history는 UTC로 저장되므로(report_optimization) '오늘 0시'도 UTC 기준으로 계산
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_killed = (
        db.query(func.count(OptimizationHistory.id))
        .filter(OptimizationHistory.timestamp >= today_start)
        .scalar()
    ) or 0

    return {
        "totalMachines": total_machines,
        "onlineMachines": online_machines,
        "avgCpuUsage": round(avg_cpu, 1),
        "avgRamUsage": round(avg_ram, 1),
        "todayKilledCount": today_killed,
    }
