"""텔레메트리 관련 API.

- POST /api/v1/metrics          : 텔레메트리 데이터 수신 및 DB 저장
- GET  /status                  : 모바일 대시보드용 최신 상태 조회
- GET  /api/v1/logs             : 텔레메트리 로그 조회 (웹 대시보드용)
- GET  /api/v1/metrics/history  : 모바일 앱용 최근 24개 추이 데이터
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import TelemetryLog, ProcessLog
from routers.control import pop_pending_command, set_latest_client_ip
from schemas import TelemetryData, TelemetryResponse

router = APIRouter()

# RAM 실수치 및 GPU 온도 캐시 (DB 스키마 변경 없이 메모리 유지)
_latest_ram_used_gb: float = 0.0
_latest_ram_total_gb: float = 0.0
_latest_gpu_temp: float = 0.0


# 텔레메트리 데이터 수신 및 DB 저장
@router.post("/api/v1/metrics")
async def receive_metrics(
    data: TelemetryData,
    request: Request,
    db: Session = Depends(get_db),
):
    global _latest_ram_used_gb, _latest_ram_total_gb, _latest_gpu_temp
    print(f"[{data.timestamp}] 수신 시도: {data.machineId}")
    print(f" C#이 보낸 GPU 온도 원본: {data.gpuTemperatureCelsius} 도")

    if request.client and request.client.host:
        set_latest_client_ip(request.client.host)

    _latest_ram_used_gb = data.ramUsedGb
    _latest_ram_total_gb = data.ramTotalGb
    if data.gpuTemperatureCelsius is not None:
        _latest_gpu_temp = data.gpuTemperatureCelsius

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
        pending_cmd = pop_pending_command()
        print(f"✅ [{data.machineId}] MySQL 데이터 저장 성공 (프로세스 {len(data.topProcesses)}건 포함, pendingCommand={pending_cmd})")
        return {
            "status": "success",
            "message": "데이터가 DB에 저장되었습니다.",
            "pendingCommand": pending_cmd,
        }

    except Exception as e:
        db.rollback()
        print(f"❌ DB 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# 모바일 대시보드용 최신 상태 조회
@router.get("/status")
async def get_status():
    db = SessionLocal()
    try:
        result = db.query(TelemetryLog).order_by(TelemetryLog.timestamp.desc()).first()
        if result:
            return {
                "cpu": result.cpuUsage,
                "ram": result.ramUsage,
                "gpu": result.gpuUsage,
                "gpuTemp": _latest_gpu_temp,
                "ram_used": _latest_ram_used_gb,
                "ram_total": _latest_ram_total_gb,
            }
        return {"cpu": 0, "ram": 0, "gpu": 0, "gpuTemp": 0, "ram_used": 0, "ram_total": 0}
    finally:
        db.close()


# 텔레메트리 데이터 조회 (웹 대시보드용)
@router.get("/api/v1/logs", response_model=List[TelemetryResponse])
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(TelemetryLog).order_by(desc(TelemetryLog.timestamp)).limit(limit).all()
    return logs


# 모바일 앱용 최근 24개 추이 데이터
@router.get("/api/v1/metrics/history")
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
