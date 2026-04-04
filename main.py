from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from datetime import datetime

# UPM FastAPI 서버 인스턴스 생성
app = FastAPI(title="UPM Global Optimization Server", version="3.0")

# [데이터 모델 정의] JSON 명세서와 1:1 매칭 (camelCase 유지)
class ProcessInfo(BaseModel):
    processId: int
    processName: str
    memoryWorkingSetBytes: int
    isSystemCritical: bool

class TelemetryData(BaseModel):
    machineId: str
    cpuUsagePercent: float
    ramUsagePercent: float
    gpuTemperatureCelsius: float
    timestamp: datetime
    topProcesses: List[ProcessInfo]

# 📊 2.1. [REST API] 텔레메트리 & 프로세스 수신 (Desktop ➔ Server)
@app.post("/api/v1/metrics")
async def receive_metrics(data: TelemetryData):
    # C# 메인 프로그램에서 보낸 JSON 데이터가 data 객체로 자동 변환 및 검증됩니다.
    print(f"[{data.timestamp}] 수신 완료: {data.machineId}")
    print(f"하드웨어 상태 ➔ CPU: {data.cpuUsagePercent}%, RAM: {data.ramUsagePercent}%")
    print(f"수집된 프로세스 수 ➔ {len(data.topProcesses)}개")
    
    # TODO: 추후 여기에 MySQL(MariaDB) DB 저장 로직이 추가됩니다.
    
    return {"status": "success", "message": "텔레메트리 데이터가 성공적으로 수신되었습니다."}

# 🛡️ 2.2. [REST API] 글로벌 최적화 룰셋 반환 (Server ➔ Desktop)
@app.get("/api/v1/optimization/rules")
async def get_optimization_rules():
    # C# 메인 프로그램이 이 주소로 요청하면 아래 JSON을 그대로 반환합니다.
    # TODO: 추후 DB에서 실시간 분석된 블랙리스트를 가져오도록 연동합니다.
    return {
      "version": "v1.0.5",
      "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
      "blackList": ["bloatware.exe", "adware_updater.exe", "heavy_background_miner.exe"],
      "whiteList": ["svchost", "explorer", "System", "csrss"]
    }