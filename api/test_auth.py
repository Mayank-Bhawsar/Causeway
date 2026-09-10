from __future__ import annotations

import pytest
from starlette.requests import Request

from api.auth import ApiKeyMiddleware, check_api_key, extract_api_key


def _request(headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw,
    }
    return Request(scope)


def test_extract_bearer():
    req = _request({"Authorization": "Bearer secret-token"})
    assert extract_api_key(req) == "secret-token"


def test_extract_x_api_key():
    req = _request({"X-API-Key": "key123"})
    assert extract_api_key(req) == "key123"


def test_check_api_key_open_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INGEST_API_KEY", raising=False)
    assert check_api_key(_request(), None, "ingest") is None


def test_check_api_key_rejects(monkeypatch: pytest.MonkeyPatch):
    err = check_api_key(_request(), "expected", "ingest")
    assert err is not None
    assert err.status_code == 401


def test_check_api_key_accepts_bearer():
    req = _request({"Authorization": "Bearer expected"})
    assert check_api_key(req, "expected", "ingest") is None


def test_middleware_blocks_ingest_without_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_API_KEY", "write-key")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(ApiKeyMiddleware)

    @app.post("/ingest/alerts")
    async def stub() -> dict:
        return {"ok": True}

    client = TestClient(app)
    r = client.post("/ingest/alerts", json={"alerts": []})
    assert r.status_code == 401
    r2 = client.post(
        "/ingest/alerts",
        json={"alerts": []},
        headers={"Authorization": "Bearer write-key"},
    )
    assert r2.status_code == 200


def test_middleware_read_key_on_get(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_READ_KEY", "read-key")
    monkeypatch.delenv("INGEST_API_KEY", raising=False)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(ApiKeyMiddleware)

    @app.get("/api/v1/incidents")
    async def stub() -> dict:
        return {"incidents": []}

    client = TestClient(app)
    assert client.get("/api/v1/incidents").status_code == 401
    assert (
        client.get("/api/v1/incidents", headers={"X-API-Key": "read-key"}).status_code == 200
    )


def test_healthz_stays_public(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_READ_KEY", "read-key")
    monkeypatch.setenv("INGEST_API_KEY", "write-key")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(ApiKeyMiddleware)

    @app.get("/healthz")
    async def health() -> dict:
        return {"status": "ok"}

    assert TestClient(app).get("/healthz").status_code == 200
