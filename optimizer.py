"""최적화 핵심 로직 (룰셋/화이트리스트/프로세스 판정).

- 종료 대상 판단 기준 상수 및 화이트리스트/보호목록
- 프로세스 이름 정규화(_normalize_name)
- 서버 자기 자신 보호(_strip_self_kill)
- process_logs 기반 동적 룰셋 생성(optimize_rules)
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from models import ProcessLog

# 종료 대상 판단 기준 상수
MEMORY_THRESHOLD_BYTES = 524288000        # 500MB 이상이면 고메모리 프로세스로 간주
RECENT_WINDOW = timedelta(hours=1)        # 최근 수집 기준 시간 창
BLACKLIST_MAX = 10                        # 블랙리스트 최대 개수

# 절대 종료하면 안 되는 시스템 필수 프로세스 (소문자 / 확장자 제외 기준)
WHITELIST = [
    "svchost", "explorer", "System", "csrss", "lsass", "winlogon",
    # 개발·런타임 관련 프로세스
    "python", "pythonw", "uvicorn", "node", "dotnet", "msbuild",
    "code", "devenv", "servicehub", "cmd", "powershell", "pwsh",
    "windowsterminal", "conhost", "git", "ssh",
]
_WHITELIST_SET = {name.lower() for name in WHITELIST}

# 절대 보호 목록: 창 유무·메모리와 무관하게 무조건 killList에서 제외 (소문자 / 확장자 제외 기준)
HARD_PROTECT = [
    # [VS Code / Visual Studio 관련]
    "code", "devenv", "msbuild", "servicehub", "vbcscompiler", "perfwatson2",
    # [파이썬/서버 런타임]
    "python", "pythonw", "uvicorn", "node", "dotnet",
    # [셸/터미널]
    "cmd", "powershell", "pwsh", "conhost", "windowsterminal", "git",
    # [시스템 필수] 기존 WHITELIST 항목 전부 포함
    *WHITELIST,
]
_HARD_PROTECT_SET = {name.lower() for name in HARD_PROTECT}

# killList에서 점수와 무관하게 항상 제거해야 하는 프로세스.
# 이 서버 자체가 python 프로세스라, killList에 들어가면 서버가 자기 자신을 종료하게 된다.
_ALWAYS_EXCLUDE_FROM_KILL = {"python", "pythonw", "uvicorn"}


def _normalize_name(name: str) -> str:
    """프로세스 이름을 소문자로 정규화하고 .exe 확장자를 제거한다."""
    n = (name or "").strip().lower()
    if n.endswith(".exe"):
        n = n[:-4]
    return n


def _strip_self_kill(kill_list: list) -> list:
    """killList에서 서버 자신을 죽일 수 있는 프로세스(python/pythonw/uvicorn)를 항상 제거한다."""
    return [name for name in kill_list if _normalize_name(name) not in _ALWAYS_EXCLUDE_FROM_KILL]


def optimize_rules(db: Session) -> dict:
    """process_logs를 분석해 동적으로 최적화 룰셋(블랙/화이트리스트)을 생성한다."""
    # 1. 최근 수집된 프로세스 기준 시점 확인
    latest_ts = db.query(func.max(ProcessLog.timestamp)).scalar()

    # 2. 블랙리스트 후보 집계
    #    - isSystemCritical == False
    #    - memoryWorkingSetBytes >= 500MB
    #    - 전체 PC에서 등장 빈도(freq)가 높은 순서
    query = db.query(
        ProcessLog.processName,
        func.count(ProcessLog.id).label("freq"),
    ).filter(
        ProcessLog.isSystemCritical == False,  # noqa: E712 (SQLAlchemy 컬럼 비교)
        ProcessLog.memoryWorkingSetBytes >= MEMORY_THRESHOLD_BYTES,
    )

    # "최근 수집된" 데이터만 대상으로 제한
    if latest_ts is not None:
        query = query.filter(ProcessLog.timestamp >= latest_ts - RECENT_WINDOW)

    rows = query.group_by(ProcessLog.processName).order_by(desc("freq")).all()

    # 3. 화이트리스트에 해당하는 프로세스는 블랙리스트에서 제외
    black_list = []
    for name, _freq in rows:
        if not name or _normalize_name(name) in _WHITELIST_SET:
            continue
        black_list.append(name)
        if len(black_list) >= BLACKLIST_MAX:
            break

    # 안전장치: 점수/빈도와 무관하게 python/pythonw/uvicorn은 killList에서 항상 제거
    black_list = _strip_self_kill(black_list)

    # 4. 결과 반환
    return {
        "version": "v2.0.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "blackList": black_list,
        "whiteList": WHITELIST,
    }
