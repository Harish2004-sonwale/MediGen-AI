"""Production Security Headers Middleware.

Phase 9.0.30: Production Hardening, High Availability & Enterprise Platform Release.

Provides hardened HTTP response headers for all outbound responses:
- X-Content-Type-Options: nosniff (prevents MIME-type sniffing)
- X-Frame-Options: DENY (clickjacking protection)
- Referrer-Policy: strict-origin-when-cross-origin (privacy protection)
- Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
- Strict-Transport-Security (HSTS in production or HTTPS)
- Content-Security-Policy (CSP) tailored for medical web applications
"""

from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware injecting production-grade security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        # 1. MIME Sniffing Protection
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Clickjacking Frame Protection
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 4. Permissions Policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # 5. Strict-Transport-Security (HSTS)
        if settings.is_production() or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # 6. Content-Security-Policy (skip or relax for Swagger / Redoc interactive docs)
        path = request.url.path
        if not (path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json")):
            csp_policy = (
                "default-src 'self'; "
                "img-src 'self' data: blob:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss: http: https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self';"
            )
            response.headers["Content-Security-Policy"] = csp_policy

        return response
