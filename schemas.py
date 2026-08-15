"""Pydantic 모델 (API 요청/응답 데이터 검증용).

- ProcessInfo        : 프로세스 1건 정보
- TelemetryData      : C# 에이전트가 보내는 텔레메트리 수신 데이터
- TelemetryResponse  : 웹 대시보드로 내보내는 로그 응답
- AnalyzeRequest     : 실시간 프로세스 분석 요청
- ExceptionRequest   : 사용자 예외 목록 관리 요청
- ReportRequest      : 종료 이력 기록 요청
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


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
    gpuUsagePercent: Optional[float] = None        # 새 에이전트용
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


class AnalyzeRequest(BaseModel):
    machineId: str
    topProcesses: List[ProcessInfo] = []


class ExceptionRequest(BaseModel):
    machineId: str
    processName: str
    action: str = "add"   # "add" = 예외 등록, "remove" = 예외 삭제


class ReportRequest(BaseModel):
    machineId: str
    killedProcesses: List[str] = []
