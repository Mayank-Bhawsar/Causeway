from __future__ import annotations

import os

import httpx


async def notify_incident_created(
    incident_id: str,
    *,
    signal_count: int,
    nodes: list[str],
    top_cause: str | None,
) -> None:
    url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        return

    api = os.getenv("CAUSEWAY_PUBLIC_URL", "http://localhost:8000")
    lines = [
        f"*Causeway incident* `{incident_id}`",
        f"Signals: {signal_count}",
        f"Services: {', '.join(nodes[:8])}",
    ]
    if top_cause:
        lines.append(f"Top cause candidate: `{top_cause}`")
    lines.append(f"<{api}/api/v1/incidents/{incident_id}|Open in API>")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"text": "\n".join(lines)})
    except Exception as exc:  # noqa: BLE001
        print(f"slack notify failed: {exc}", flush=True)
