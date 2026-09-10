"""Worker liveness: heartbeat file + minimal HTTP /healthz (Phase K3)."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path


def heartbeat_path() -> Path:
    return Path(os.getenv("WORKER_HEARTBEAT_PATH", "/tmp/causeway_worker_heartbeat"))


def write_heartbeat(extra: dict | None = None) -> None:
    payload = {"ts": time.time(), "status": "ok"}
    if extra:
        payload.update(extra)
    heartbeat_path().write_text(json.dumps(payload), encoding="utf-8")


async def heartbeat_loop() -> None:
    interval = int(os.getenv("WORKER_HEARTBEAT_SEC", "30"))
    while True:
        try:
            write_heartbeat()
            print(f"worker heartbeat ts={time.time():.0f}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"heartbeat_loop error: {exc}", flush=True)
        await asyncio.sleep(interval)


def _heartbeat_age_sec() -> float | None:
    try:
        data = json.loads(heartbeat_path().read_text(encoding="utf-8"))
        return time.time() - float(data.get("ts", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


async def _handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    try:
        request_line = (await reader.readline()).decode("utf-8", errors="ignore").strip()
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break

        max_age = float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SEC", "120"))
        age = _heartbeat_age_sec()
        if request_line.startswith("GET /healthz"):
            if age is not None and age <= max_age:
                body = json.dumps({"status": "ok", "heartbeat_age_sec": round(age, 1)})
                status_line = "HTTP/1.1 200 OK"
            else:
                body = json.dumps(
                    {
                        "status": "stale",
                        "heartbeat_age_sec": None if age is None else round(age, 1),
                    }
                )
                status_line = "HTTP/1.1 503 Service Unavailable"
        else:
            body = '{"detail":"not found"}'
            status_line = "HTTP/1.1 404 Not Found"

        encoded = body.encode("utf-8")
        header = (
            f"{status_line}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(encoded)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + encoded)
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def health_server() -> None:
    port = int(os.getenv("WORKER_HEALTH_PORT", "8085"))
    server = await asyncio.start_server(_handle_client, "0.0.0.0", port)
    addr = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    print(f"worker health listening on {addr}", flush=True)
    async with server:
        await server.serve_forever()
