from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
# --- DB 관련 라이브러리 ---
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uvicorn

# [1. DB 설정 및 엔진 생성]
# '1234' 부분을 MySQL 비밀번호로 다시 한번 확인하세요.
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/upmdecode"

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
    gpuTemp = Column(Float)
    timestamp = Column(DateTime)

# 서버 실행 시 테이블 자동 생성
Base.metadata.create_all(bind=engine)

# [3. DB 세션 관리 함수 (Dependency Injection)]
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# [4. FastAPI 앱 초기화]
app = FastAPI(title="UPM Global Optimization Server", version="3.0")

# [5. Pydantic 모델 (데이터 검증용)]
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
    topProcesses: List[ProcessInfo] = []

# [6. API 엔드포인트]

# 📊 6.1. 텔레메트리 데이터 수신 및 DB 저장
@app.post("/api/v1/metrics")
async def receive_metrics(data: TelemetryData, db: Session = Depends(get_db)):
    print(f"[{data.timestamp}] 수신 시도: {data.machineId}")
    
    try:
        new_log = TelemetryLog(
            machineId=data.machineId,
            cpuUsage=data.cpuUsagePercent,
            ramUsage=data.ramUsagePercent,
            gpuTemp=data.gpuTemperatureCelsius,
            timestamp=data.timestamp
        )
        db.add(new_log)
        db.commit()
        print(f"✅ [{data.machineId}] MySQL 데이터 저장 성공")
        return {"status": "success", "message": "데이터가 DB에 저장되었습니다."}
    
    except Exception as e:
        db.rollback() # 오류 발생 시 되돌리기
        print(f"❌ DB 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 🛡️ 6.2. 글로벌 최적화 룰셋 반환
@app.get("/api/v1/optimization/rules")
async def get_optimization_rules():
    return {
      "version": "v1.0.5",
      "updatedAt": datetime.now(timezone.utc).isoformat(),
      "blackList": ["bloatware.exe", "adware_updater.exe", "heavy_background_miner.exe"],
      "whiteList": ["svchost", "explorer", "System", "csrss"]
    }

# [7. 서버 실행]
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)