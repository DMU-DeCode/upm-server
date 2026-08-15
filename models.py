"""DB 테이블 정의 (SQLAlchemy ORM 모델).

- TelemetryLog        : CPU/RAM/GPU 텔레메트리 로그
- ProcessLog          : 수집된 프로세스 스냅샷 로그
- UserException       : machineId별 '절대 종료 금지' 예외 목록
- OptimizationHistory : 실제로 종료된 프로세스 이력
"""

from sqlalchemy import Column, Integer, BigInteger, Float, String, Boolean, DateTime

from database import Base


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
