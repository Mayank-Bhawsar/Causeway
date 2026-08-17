"""Poll VM for per-service server latency; emit SignalKind.TRACE_LATENCY_SHIFT."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import httpx

from api.models.signal import Signal, SignalKind

VM_URL = os.getenv("VM_URL", "http://victoria-metrics:8428")
THRESHOLD_MS = float(os.getenv("DETECT_LATENCY_MS", "200"))

QUERY = """
(
  sum by (service_name) (
    increase(traces_span_metrics_duration_milliseconds_sum{span_kind="SPAN_KIND_SERVER"}[1m])
  )
  /
  sum by (service_name) (
    increase(traces_span_metrics_duration_milliseconds_count{span_kind="SPAN_KIND_SERVER"}[1m])
  )
)
"""


async def fetch_latency_by_service() -> dict[str, float]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{VM_URL}/api/v1/query", params={"query": QUERY})
        r.raise_for_status()
        out: dict[str, float] = {}
        for row in r.json().get("data", {}).get("result", []):
            svc = row["metric"].get("service_name")
            if not svc:
                continue
            out[svc] = float(row["value"][1])
        return out


async def detect_latency_signals() -> list[Signal]:
    now = datetime.now(timezone.utc)
    lat = await fetch_latency_by_service()
    signals: list[Signal] = []
    for svc, ms in lat.items():
        if ms <= THRESHOLD_MS:
            continue
        # severity scales from threshold→1s
        sev = min(1.0, max(0.4, (ms - THRESHOLD_MS) / 800.0))
        signals.append(
            Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:16]}",
                kind=SignalKind.TRACE_LATENCY_SHIFT,
                node_id=f"svc:{svc}",
                severity=sev,
                onset_at=now,
                observed_at=now,
                fingerprint=f"latency:{svc}",
                payload={"service_name": svc, "latency_ms": ms, "threshold_ms": THRESHOLD_MS},
            )
        )
    return signals