"""모바일 앱 제어 명령 API.

- POST /optimize  : 빠른 최적화 명령 처리 (내부망 8787 직접 전달 + 외부망 피기백 큐 폴백)
- POST /shutdown  : PC 종료 명령 처리 (내부망 8787 직접 전달 + 외부망 피기백 큐 폴백)
- POST /restart   : PC 재시작 명령 처리 (내부망 8787 직접 전달 + 외부망 피기백 큐 폴백)
"""

from collections import deque
import os
from typing import Deque, Optional

from fastapi import APIRouter
import httpx

router = APIRouter()

# 가장 최근에 메트릭을 전송한 PC의 IP 및 대기 명령 큐 (외부 망 피기백 전달용)
_latest_client_ip: Optional[str] = None
_pending_commands: Deque[str] = deque(maxlen=10)


def set_latest_client_ip(ip: Optional[str]) -> None:
    """메트릭 수신 시 클라이언트 IP를 갱신한다."""
    global _latest_client_ip
    if ip and ip not in ("127.0.0.1", "::1", "localhost"):
        _latest_client_ip = ip


def enqueue_command(command: str) -> None:
    """직접 릴레이(8787)가 불가능한 외부 망 환경을 위해 대기 큐에 명령을 넣는다."""
    if command not in _pending_commands:
        _pending_commands.append(command)


def pop_pending_command() -> Optional[str]:
    """PC 클라이언트가 POST /api/v1/metrics 호출 시 대기 중인 명령 1건을 꺼내간다."""
    if _pending_commands:
        return _pending_commands.popleft()
    return None


def _resolve_target_base_url() -> Optional[str]:
    """환경변수 UPM_CLIENT_URL 또는 최근 메트릭 송신 PC의 IP로 8787 주소를 조합한다."""
    env_url = os.getenv("UPM_CLIENT_URL", "").strip().rstrip("/")
    if env_url:
        return env_url
    if _latest_client_ip:
        return f"http://{_latest_client_ip}:8787"
    return None


async def _relay_or_enqueue(command: str, label: str) -> dict:
    """
    1순위: 같은 내부망(LAN)에 있는 PC의 MobileControlHttpServer(8787)로 즉시 HTTP POST 전달
    2순위: 외부 망(NAT/ngrok)이라 8787 직접 접속이 안 되면 대기 큐에 적재 → 다음 메트릭 응답(최대 5초 내)에 피기백 전달
    """
    target_base = _resolve_target_base_url()
    if target_base:
        target_url = f"{target_base}/{command}"
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(target_url)
                if resp.status_code == 200:
                    print(f"✅ [{label}] PC 직접 전달 성공 ({target_url})")
                    try:
                        data = resp.json()
                        if isinstance(data, dict):
                            data.setdefault("status", "success")
                            data["mode"] = "direct"
                            return data
                    except Exception:
                        pass
                    return {"status": "success", "mode": "direct", "message": f"{label} 명령을 실행했습니다."}
        except Exception as e:
            print(f"ℹ️ [{label}] 직접 전달 실패({target_url}: {e}) → 외부 망 피기백 큐로 전환")

    enqueue_command(command)
    print(f"📥 [{label}] 명령 큐 등록 완료 (다음 메트릭 동기화 시 PC에서 즉시 실행)")
    return {
        "status": "success",
        "mode": "queued",
        "message": f"{label} 명령이 접수되었습니다 (최대 5초 내 PC에서 실행됩니다).",
    }


# 모바일 앱 빠른 최적화 명령 처리
@router.post("/optimize")
async def optimize_system():
    print(" [명령 수신] 스마트폰 앱으로부터 시스템 최적화 명령을 받았습니다!")
    return await _relay_or_enqueue("optimize", "빠른 최적화")


# 모바일 앱 PC 종료 명령 처리
@router.post("/shutdown")
async def shutdown():
    print(" [명령 수신] 스마트폰 앱으로부터 PC 종료 명령을 받았습니다!")
    return await _relay_or_enqueue("shutdown", "PC 종료")


# 모바일 앱 PC 재시작 명령 처리
@router.post("/restart")
async def restart():
    print(" [명령 수신] 스마트폰 앱으로부터 PC 재시작 명령을 받았습니다!")
    return await _relay_or_enqueue("restart", "PC 재시작")
