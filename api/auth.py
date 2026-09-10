"""Optional API keys for ingest (write) and read routes (Phase K)."""
from __future__ import annotations

import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def extract_api_key(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    header = request.headers.get("x-api-key")
    if header:
        return header.strip()
    return None


def _expected_key(env_name: str) -> str | None:
    value = os.getenv(env_name, "").strip()
    return value or None


def check_api_key(request: Request, expected: str | None, purpose: str) -> JSONResponse | None:
    """Return 401 response if key required but missing/invalid; else None."""
    if not expected:
        return None
    provided = extract_api_key(request) or ""
    if not secrets.compare_digest(provided, expected):
        return JSONResponse(
            status_code=401,
            content={"detail": f"Missing or invalid API key ({purpose})"},
        )
    return None


def _is_public_path(path: str) -> bool:
    if path == "/healthz":
        return True
    if path in ("/", "/ui", "/ui/"):
        return True
    if path.startswith("/ui/"):
        return True
    return False


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _is_public_path(path):
            return await call_next(request)

        ingest_key = _expected_key("INGEST_API_KEY")
        read_key = _expected_key("API_READ_KEY")

        if path.startswith("/ingest"):
            err = check_api_key(request, ingest_key, "ingest")
            if err:
                return err
        elif path.startswith("/api/v1"):
            if request.method == "GET":
                err = check_api_key(request, read_key, "read")
            else:
                err = check_api_key(request, ingest_key, "write")
            if err:
                return err

        return await call_next(request)
