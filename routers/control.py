"""모바일 앱 제어 명령 API.

- POST /optimize  : 빠른 최적화 명령 처리
- POST /shutdown  : PC 종료 명령 처리
- POST /restart   : PC 재시작 명령 처리
"""

import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException

# 같은 PC에서 실행 중인 UPM PC 프로그램(MobileControlHttpServer)의 로컬 제어 주소
AGENT_CONTROL_URL = "http://127.0.0.1:8787"
# 최적화는 프로세스 종료를 기다리므로 여유 있게 대기
AGENT_OPTIMIZE_TIMEOUT_SEC = 25

router = APIRouter()


# 모바일 앱 빠른 최적화 명령 처리
# PC 프로그램의 로컬 제어 포트(8787)로 전달해, PC의 "빠른 최적화" 버튼과 같은 동작을 실행한다.
# (동기 함수로 두면 FastAPI가 별도 스레드에서 실행하므로 대기 중에도 다른 요청이 막히지 않는다.)
@router.post("/optimize")
def optimize_system():
    print(" [명령 수신] 스마트폰 앱으로부터 시스템 최적화 명령을 받았습니다! → PC 프로그램으로 전달")
    req = urllib.request.Request(
        f"{AGENT_CONTROL_URL}/optimize",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=AGENT_OPTIMIZE_TIMEOUT_SEC) as res:
            body = json.loads(res.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        print(f"❌ PC 프로그램 최적화 실패 (HTTP {e.code})")
        raise HTTPException(status_code=502, detail="PC 프로그램에서 최적화에 실패했습니다.")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"❌ PC 프로그램에 연결할 수 없습니다: {e}")
        raise HTTPException(
            status_code=503,
            detail="PC 프로그램에 연결할 수 없습니다. PC에서 UPM이 실행 중인지 확인해 주세요.",
        )

    cleared = body.get("clearedProcesses", 0)
    print(f" ✅ PC 최적화 완료: {cleared}개 프로세스 정리")
    return {
        "status": "success",
        "message": "Optimization completed",
        "clearedProcesses": cleared,
    }


# 모바일 앱 PC 종료 명령 처리
@router.post("/shutdown")
async def shutdown():
    try:
        print(" [명령 수신] 스마트폰 앱으로부터 PC 종료 명령을 받았습니다!")

        # [같은 PC] 현재 사용
        os.system("shutdown /s /t 3")

        # [다른 PC] 추후 사용 - MobileControlHttpServer(8787)로 릴레이
        # async with httpx.AsyncClient() as client:
        #     await client.post("http://127.0.0.1:8787/shutdown")

        print(" PC 종료 명령 실행 완료 (3초 후 종료됩니다)")
        return {"status": "success", "message": "PC 종료 명령을 실행합니다."}
    except Exception as e:
        print(f"❌ 종료 명령 실행 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="종료 명령 수행 실패")


# 모바일 앱 PC 재시작 명령 처리
@router.post("/restart")
async def restart():
    try:
        print(" [명령 수신] 스마트폰 앱으로부터 PC 재시작 명령을 받았습니다!")

        # [같은 PC] 현재 사용
        os.system("shutdown /r /t 3")

        # [다른 PC] 추후 사용 - MobileControlHttpServer(8787)로 릴레이
        # async with httpx.AsyncClient() as client:
        #     await client.post("http://127.0.0.1:8787/restart")

        print(" PC 재시작 명령 실행 완료 (3초 후 재시작됩니다)")
        return {"status": "success", "message": "PC 재시작 명령을 실행합니다."}
    except Exception as e:
        print(f"❌ 재시작 명령 실행 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="재시작 명령 수행 실패")
