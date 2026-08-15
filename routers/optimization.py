"""최적화 관련 API (룰셋/분석/예외/이력).

- GET  /api/v1/optimization/rules       : 글로벌 최적화 룰셋 반환 (DB 기반 동적 생성)
- POST /api/v1/optimization/analyze     : 실시간 프로세스 분석 → 종료 대상(killList) 산출
- POST /api/v1/optimization/exceptions  : 사용자 예외 목록 등록/삭제
- GET  /api/v1/optimization/exceptions  : 사용자 예외 목록 조회
- POST /api/v1/optimization/report      : 실제 종료된 프로세스 이력 기록
- GET  /api/v1/optimization/history     : 종료 이력 조회
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from models import UserException, OptimizationHistory
from schemas import AnalyzeRequest, ExceptionRequest, ReportRequest
from optimizer import (
    _HARD_PROTECT_SET,
    _normalize_name,
    _strip_self_kill,
    optimize_rules,
)

router = APIRouter(prefix="/api/v1/optimization")


# 글로벌 최적화 룰셋 반환 (DB 기반 동적 생성)
@router.get("/rules")
async def get_optimization_rules(db: Session = Depends(get_db)):
    return optimize_rules(db)


# 실시간 프로세스 분석 (C# 에이전트가 보낸 프로세스를 즉시 종료 대상으로 변환)
@router.post("/analyze")
async def analyze_processes(req: AnalyzeRequest, db: Session = Depends(get_db)):
    # "고클린 방식" 판정 순서 (아래 4개 중 하나라도 걸리면 제외, 나머지는 전부 종료)
    #  1) isSystemCritical == True → 제외
    #  2) HARD_PROTECT 목록에 있는 이름 → 제외 (개발환경 보호)
    #  3) 사용자 예외 목록(user_exceptions)에 등록된 프로세스 → 제외 (사용자 화이트리스트)
    #  4) isCurrentUserOwned == False → 제외 (SYSTEM/서비스 계정 보호)
    #  그 외 모든 프로세스 → 메모리·CPU·창 유무와 무관하게 종료

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

        # 1) 시스템 필수 프로세스 → 제외
        # 2) HARD_PROTECT 목록(개발환경 보호) → 제외
        if proc.isSystemCritical or norm_name in _HARD_PROTECT_SET:
            _log("HARD_PROTECT")
            continue
        # 3) 사용자 예외 목록(화이트리스트) → 제외
        if norm_name in exception_set:
            _log("사용자예외")
            continue
        # 4) 현재 사용자 계정 소유가 아님(SYSTEM/서비스 계정) → 제외
        if not proc.isCurrentUserOwned:
            _log("SYSTEM소유")
            continue

        # 위 4개 중 어디에도 안 걸리면 메모리·CPU·창 유무와 무관하게 종료
        _log("KILL")
        kill_list.append(proc.processName)

    # 안전장치: 점수와 무관하게 python/pythonw/uvicorn은 killList에서 항상 제거
    # (이 서버 자체가 python 프로세스라 자기 자신을 종료하는 것을 방지)
    kill_list = _strip_self_kill(kill_list)

    print(f"🔍 [{req.machineId}] 분석 완료: 종료 대상 {len(kill_list)}건 → {kill_list}")
    return {"killList": kill_list}


# 사용자 예외 목록 관리 (machineId별 '절대 종료 금지' 프로세스)
@router.post("/exceptions")
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


@router.get("/exceptions")
async def list_exceptions(machineId: str, db: Session = Depends(get_db)):
    exceptions = [
        row.processName
        for row in db.query(UserException.processName)
        .filter(UserException.machineId == machineId)
        .all()
    ]
    return {"machineId": machineId, "exceptions": exceptions}


# 종료 이력 기록/조회 (실제로 종료된 프로세스를 별도로 기록)
@router.post("/report")
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


@router.get("/history")
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
