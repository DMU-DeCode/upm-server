from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import mysql.connector

app = FastAPI(title="UPM Global Server")

# --- 🛠️ DB 연결 설정 (사용자님 환경에 맞게 수정 필수) ---
db_config = {
    "host": "localhost",
    "user": "root",          # MySQL 아이디
    "password": "1234", # 🚨 실제 MySQL 비밀번호를 넣으세요!
    "database": "upmdecode"     # 생성한 데이터베이스 이름
}

def save_to_db(query, values):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        # DB 저장에 실패했을 때만 에러 메시지 출력
        print(f"❌ DB 저장 에러: {e}")
        return False

# --- 📋 데이터 모델 (C# 모델과 1:1 매칭)  ---
class HardwareSpecModel(BaseModel):
    cpuName: str = "Unknown"
    cpuCores: int = 0
    cpuThreads: int = 0
    ramTotal: str = "0 GB"
    gpuName: str = "Unknown"
    mainboard: str = "Unknown"

class SystemStatusModel(BaseModel):
    cpuUsage: float = 0.0
    cpuStatus: Optional[str] = None
    ramUsage: float = 0.0
    ramStatus: Optional[str] = None
    gpuTemperature: float = 0.0
    diskUsage: float = 0.0
    diskStatus: Optional[str] = None
    timestamp: datetime = datetime.now()
    pcName: Optional[str] = "Unknown"

# --- 🚀 API 엔드포인트 ---

@app.post("/api/v1/specs")
async def receive_specs(data: HardwareSpecModel):
    # 출력
    print(f"🖥️ [기기 등록] {data.cpuName}")
    
    # DB 저장 (테이블명은 hardware_specs로 가정)
    query = """INSERT INTO hardware_specs (cpu_name, cpu_cores, cpu_threads, ram_total, gpu_name, mainboard) 
               VALUES (%s, %s, %s, %s, %s, %s)"""
    values = (data.cpuName, data.cpuCores, data.cpuThreads, data.ramTotal, data.gpuName, data.mainboard)
    
    if save_to_db(query, values):
        print("✅ DB 저장 완료")
        
    return {"status": "success"}

@app.post("/api/v1/status")
async def receive_status(data: SystemStatusModel):
    # 1. 실제 수치 출력 (요청하신 부분)
    print(f"📡 [{data.pcName}] CPU: {data.cpuUsage}% | RAM: {data.ramUsage}% | GPU: {data.gpuTemperature}°C")
    
    # 2. DB 저장 (테이블명은 system_status로 가정) 
    query = """INSERT INTO system_status (pc_name, cpu_usage, ram_usage, gpu_temp, disk_usage, captured_at) 
               VALUES (%s, %s, %s, %s, %s, %s)"""
    values = (data.pcName, data.cpuUsage, data.ramUsage, data.gpuTemperature, data.diskUsage, data.timestamp)
    
    # 3. 저장 완료 메시지 출력
    if save_to_db(query, values):
        print("✅ DB 저장 완료")
        
    return {"status": "success"}