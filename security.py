import os
from typing import Any, Dict, List
from urllib.parse import urlparse
from flask import Request, Response


DEFAULT_ALLOWED_ORIGINS = ("https://chat.project-kk.com", "http://localhost:5173")


def get_allowed_origins() -> List[str]:
    """
    許可されたオリジンのリストを取得する
    
    環境変数 `ALLOWED_ORIGINS` とデフォルト値をマージして返します。
    """
    frontend_origin = os.getenv("FRONTEND_ORIGIN", DEFAULT_ALLOWED_ORIGINS[0])
    raw_origins = os.getenv("ALLOWED_ORIGINS", frontend_origin).split(",")
    allowed = [origin.strip() for origin in raw_origins if origin.strip()]
    for origin in DEFAULT_ALLOWED_ORIGINS:
        if origin not in allowed:
            allowed.append(origin)
    return allowed


def _origin_from_referer(referer: str) -> str:
    """
    Refererヘッダーからオリジン（スキーム + ホスト）を抽出する
    """
    try:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return ""
    return ""


def is_csrf_valid(request: Request) -> bool:
    """
    CSRF（クロスサイトリクエストフォージェリ）検証を行う
    
    1. リクエストメソッドが安全な場合（GET, HEAD, OPTIONS）はスルー
    2. Originヘッダーが許可リストにあるか確認
    3. Originがない場合、Refererヘッダーを確認
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return True

    allowed = get_allowed_origins()
    origin = request.headers.get("Origin")
    if origin:
        return origin in allowed

    referer = request.headers.get("Referer")
    if referer:
        referer_origin = _origin_from_referer(referer)
        return referer_origin in allowed if referer_origin else False

    allow_missing = os.getenv("ALLOW_MISSING_ORIGIN", "false").lower() in ("1", "true", "yes")
    return allow_missing


def should_set_secure_cookie(request: Request) -> bool:
    """
    CookieにSecure属性を付与すべきか判定する
    
    本番環境やHTTPS接続時にはTrueを返します。ローカル開発環境ではFalseになる場合があります。
    """
    env_value = os.getenv("COOKIE_SECURE", "").strip().lower()
    if env_value:
        return env_value in ("1", "true", "yes")

    if request.is_secure:
        return True

    host = request.headers.get("Host", "")
    if "localhost" in host or "127.0.0.1" in host:
        return False

    return True


def cookie_settings(request: Request) -> Dict[str, Any]:
    """
    一貫したCookie設定パラメータを生成する
    
    HttpOnly, SameSite, Secure などのセキュリティ属性を設定します。
    """
    samesite = os.getenv("COOKIE_SAMESITE", "Lax")
    try:
        max_age = int(os.getenv("SESSION_COOKIE_MAX_AGE", "604800"))
    except ValueError:
        max_age = 604800

    return {
        "httponly": True,
        "samesite": samesite,
        "secure": should_set_secure_cookie(request),
        "path": "/",
        "max_age": max_age,
    }


def build_csp() -> str:
    """
    Content Security Policy (CSP) ヘッダー文字列を構築する
    
    XSS攻撃などのリスクを軽減するため、許可するリソースのソースを制限します。
    """
    allowed = get_allowed_origins()
    connect_sources = ["'self'"] + allowed
    style_sources = [
        "'self'",
        "'unsafe-inline'",
        "https://cdn.jsdelivr.net",
        "https://fonts.googleapis.com",
    ]
    font_sources = ["'self'", "https://fonts.gstatic.com", "data:"]
    img_sources = ["'self'", "data:"]

    return (
        "default-src 'self'; "
        f"connect-src {' '.join(connect_sources)}; "
        f"style-src {' '.join(style_sources)}; "
        "script-src 'self'; "
        f"font-src {' '.join(font_sources)}; "
        f"img-src {' '.join(img_sources)}; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )


def apply_security_headers(response: Response) -> Response:
    """
    レスポンスに各種セキュリティヘッダーを付与する
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

    csp = os.getenv("CONTENT_SECURITY_POLICY")
    if not csp:
        csp = build_csp()
    response.headers.setdefault("Content-Security-Policy", csp)

    if os.getenv("ENABLE_HSTS", "true").lower() in ("1", "true", "yes"):
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )

    return response
