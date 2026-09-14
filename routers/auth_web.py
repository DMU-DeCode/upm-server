"""관리자 웹 로그인(세션 쿠키 기반 인증).

- GET  /login  : 로그인 페이지 HTML
- POST /login  : 아이디/비밀번호 검증 → 서명 세션 쿠키 발급 후 /dashboard로 리다이렉트
- POST /logout : 세션 쿠키 삭제 후 /login으로 리다이렉트

인증 방식:
    UPM_ADMIN_USER / UPM_ADMIN_PASSWORD 환경변수와 상수시간(compare_digest) 비교.
    성공 시 UPM_SESSION_SECRET으로 HMAC-SHA256 서명한 쿠키를 발급한다.
    (외부 의존성 없이 표준 라이브러리 hmac로 서명/검증)

의존성 require_admin_session:
    세션 쿠키를 검증한다. 유효하지 않으면 /login으로 리다이렉트(303).
    관리자 웹 화면(/dashboard)과 관리자 API(/api/v1/admin/*)에만 적용한다.
    에이전트·모바일 앱이 쓰는 엔드포인트에는 절대 적용하지 않는다.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

# 관리자 자격증명/서명 키: 환경변수에서 읽고, 미설정 시 개발용 기본값 사용.
# ⚠️ 배포 환경에서는 반드시 아래 3개 환경변수를 설정할 것.
ADMIN_USER = os.environ.get("UPM_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("UPM_ADMIN_PASSWORD", "change-me")
SESSION_SECRET = os.environ.get("UPM_SESSION_SECRET", "dev-session-secret-change-me")

SESSION_COOKIE = "upm_session"
SESSION_MAX_AGE = 2 * 60 * 60  # 세션 유효기간: 2시간(초)

router = APIRouter()


# ---------------------------------------------------------------------------
# 서명 세션 토큰 (payload.signature 형식, HMAC-SHA256)
# ---------------------------------------------------------------------------
def _b64e(raw: bytes) -> str:
    """URL-safe base64 인코딩(패딩 제거)."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    """_b64e의 역연산(패딩 복원)."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    """payload 문자열을 SESSION_SECRET으로 HMAC-SHA256 서명한다."""
    mac = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256)
    return _b64e(mac.digest())


def issue_session(username: str) -> str:
    """만료시각을 포함한 서명 세션 토큰을 발급한다."""
    body = {"sub": username, "exp": int(time.time()) + SESSION_MAX_AGE}
    payload = _b64e(json.dumps(body, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload)}"


def verify_session(token: str) -> str | None:
    """세션 토큰의 서명·만료를 검증한다. 유효하면 사용자명, 아니면 None."""
    if not token or "." not in token:
        return None
    payload, sig = token.split(".", 1)
    # 서명 검증(상수시간 비교)
    if not hmac.compare_digest(sig, _sign(payload)):
        return None
    try:
        body = json.loads(_b64d(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    # 만료 검사
    if int(body.get("exp", 0)) < int(time.time()):
        return None
    return body.get("sub")


def _check_credentials(username: str, password: str) -> bool:
    """아이디/비밀번호를 환경변수 값과 상수시간 비교한다."""
    user_ok = secrets.compare_digest(username, ADMIN_USER)
    pw_ok = secrets.compare_digest(password, ADMIN_PASSWORD)
    return user_ok and pw_ok


# ---------------------------------------------------------------------------
# 인증 의존성
# ---------------------------------------------------------------------------
def require_admin_session(request: Request) -> str:
    """세션 쿠키를 검증한다. 미인증 시 /login으로 리다이렉트(303)."""
    username = verify_session(request.cookies.get(SESSION_COOKIE, ""))
    if not username:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
            detail="로그인이 필요합니다.",
        )
    return username


# ---------------------------------------------------------------------------
# 로그인 페이지
# ---------------------------------------------------------------------------
def _login_page(error: str = "") -> str:
    """로그인 페이지 HTML. error가 있으면 에러 메시지를 노출한다.
    디자인 톤은 대시보드와 통일(--primary #4f46e5, Inter 폰트, 카드 스타일)."""
    error_html = (
        f'<div class="error">{error}</div>' if error else ""
    )
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UPM 관리자 로그인</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #4f46e5;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --danger: #ef4444;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .card {{
            background: var(--card-bg);
            padding: 2.5rem 2rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            width: 100%;
            max-width: 360px;
        }}
        /* 상단 중앙 브랜드 영역. 추후 로고 이미지로 교체 예정. */
        #brand {{
            text-align: center;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 1.75rem;
            letter-spacing: 0.02em;
        }}
        label {{
            display: block;
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.375rem;
        }}
        input {{
            width: 100%;
            padding: 0.625rem 0.75rem;
            margin-bottom: 1.25rem;
            border: 1px solid #cbd5e1;
            border-radius: 0.5rem;
            font-size: 0.9375rem;
            font-family: inherit;
        }}
        input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(79,70,229,0.15);
        }}
        button {{
            width: 100%;
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.6875rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9375rem;
            transition: opacity 0.2s;
        }}
        button:hover {{ opacity: 0.9; }}
        .error {{
            background: #fee2e2;
            color: #b91c1c;
            padding: 0.625rem 0.75rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            margin-bottom: 1.25rem;
            text-align: center;
        }}
    </style>
</head>
<body>
    <form class="card" method="post" action="/login">
        <div id="brand">UPM</div>
        {error_html}
        <label for="username">아이디</label>
        <input type="text" id="username" name="username" autocomplete="username" autofocus required>
        <label for="password">비밀번호</label>
        <input type="password" id="password" name="password" autocomplete="current-password" required>
        <button type="submit">로그인</button>
    </form>
</body>
</html>
"""


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: int = 0):
    # ?error=1 이면 인증 실패 메시지 노출(POST 실패 시 리다이렉트로 전달)
    msg = "아이디 또는 비밀번호가 올바르지 않습니다." if error else ""
    return HTMLResponse(content=_login_page(msg))


@router.post("/login")
async def login(request: Request):
    # HTML 폼(application/x-www-form-urlencoded)을 표준 라이브러리로 직접 파싱한다.
    # (request.form()은 이 Starlette 버전에서 python-multipart를 요구하므로 사용하지 않음)
    body = (await request.body()).decode("utf-8", errors="replace")
    form = parse_qs(body, keep_blank_values=True)
    username = form.get("username", [""])[0]
    password = form.get("password", [""])[0]
    # 인증 실패: /login으로 되돌리고 에러 표시
    if not _check_credentials(username, password):
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_303_SEE_OTHER)
    # 인증 성공: 서명 세션 쿠키 발급 후 /dashboard로 이동
    resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=issue_session(username),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return resp


@router.post("/logout")
async def logout():
    # 쿠키 삭제 후 로그인 페이지로 이동
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(key=SESSION_COOKIE)
    return resp
