from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
# --- DB 관련 라이브러리 ---
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, desc, text, inspect as sa_inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uvicorn

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

# [6. API 엔드포인트]

# 📊 6.1. 텔레메트리 데이터 수신 및 DB 저장
@app.post("/api/v1/metrics")
async def receive_metrics(data: TelemetryData, db: Session = Depends(get_db)):
    print(f"[{data.timestamp}] 수신 시도: {data.machineId}")
    
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
        db.commit()
        print(f"✅ [{data.machineId}] MySQL 데이터 저장 성공")
        return {"status": "success", "message": "데이터가 DB에 저장되었습니다."}
    
    except Exception as e:
        db.rollback() 
        print(f"❌ DB 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 📈 6.2. 텔레메트리 데이터 조회 (대시보드용)
@app.get("/api/v1/logs", response_model=List[TelemetryResponse])
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(TelemetryLog).order_by(desc(TelemetryLog.timestamp)).limit(limit).all()
    return logs

# 🛡️ 6.3. 글로벌 최적화 룰셋 반환
@app.get("/api/v1/optimization/rules")
async def get_optimization_rules():
    return {
      "version": "v1.0.5",
      "updatedAt": datetime.now(timezone.utc).isoformat(),
      "blackList": ["bloatware.exe", "adware_updater.exe", "heavy_background_miner.exe"],
      "whiteList": ["svchost", "explorer", "System", "csrss"]
    }

# 🖥️ 6.4. 대시보드 페이지 (개선된 UI)
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
            <h1>🚀 UPM Global Control Center</h1>
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