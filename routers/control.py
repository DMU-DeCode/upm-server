"""모바일 앱 제어 명령 API.

- POST /optimize  : 빠른 최적화 명령 처리
- POST /shutdown  : PC 종료 명령 처리
- POST /restart   : PC 재시작 명령 처리
"""

import os

from fastapi import APIRouter, HTTPException

router = APIRouter()


# 모바일 앱 빠른 최적화 명령 처리
@router.post("/optimize")
async def optimize_system():
    try:
        print(" [명령 수신] 스마트폰 앱으로부터 시스템 최적화 명령을 받았습니다!")
        # 실제 최적화 로직 예시
        # import os
        # os.system("명령어")
        return {"status": "success", "message": "Optimization completed"}
    except Exception as e:
        print(f"❌ 최적화 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="최적화 명령 수행 실패")


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
