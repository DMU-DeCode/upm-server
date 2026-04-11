from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from datetime import datetime
# --- DB 관련 라이브러리 추가 ---
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uvicorn

# [DB 설정 영역]
# '비밀번호입력' 부분을 아까 MySQL 깔 때 설정한 비밀번호로 바꾸세요!
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:admin1234@localhost:3306/upm_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# [DB 테이블 정의] 엑셀의 칸을 미리 만드는 것과 같습니다.
class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    id = Column(Integer, primary_key=True, index=True)
    machineId = Column(String(50))
    cpuUsage = Column(Float)
    ramUsage = Column(Float)
    gpuTemp = Column(Float)
    timestamp = Column(DateTime)

# 서버 실행 시 DB 테이블이 없으면 자동으로 생성합니다.
Base.metadata.create_all(bind=engine)

# --- 기존 FastAPI 설정 ---
app = FastAPI(title="UPM Global Optimization Server", version="3.0")

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

# 📊 2.1. [REST API] 텔레메트리 데이터 수신 및 DB 저장
@app.post("/api/v1/metrics")
async def receive_metrics(data: TelemetryData):
    print(f"[{data.timestamp}] 수신 완료: {data.machineId}")
    
    # [추가된 로직] DB 접속 및 저장
    db = SessionLocal()
    try:
        new_log = TelemetryLog(
            machineId=data.machineId,
            cpuUsage=data.cpuUsagePercent,
            ramUsage=data.ramUsagePercent,
            gpuTemp=data.gpuTemperatureCelsius,
            timestamp=data.timestamp
        )
        db.add(new_log)  # 저장 바구니에 담기
        db.commit()      # 최종 저장 확정!
        print("✅ MySQL 데이터 저장 성공")
    except Exception as e:
        print(f"❌ DB 저장 오류: {e}")
    finally:
        db.close()       # 접속 종료 (필수!)

    return {"status": "success", "message": "데이터가 DB에 저장되었습니다."}

# 🛡️ 2.2. [REST API] 글로벌 최적화 룰셋 반환 (유지)
@app.get("/api/v1/optimization/rules")
async def get_optimization_rules():
    return {
      "version": "v1.0.5",
      "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
      "blackList": ["bloatware.exe", "adware_updater.exe", "heavy_background_miner.exe"],
      "whiteList": ["svchost", "explorer", "System", "csrss"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)