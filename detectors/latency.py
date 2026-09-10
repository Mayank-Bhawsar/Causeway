"""Poll VM for per-service server latency; emit TRACE_LATENCY_SHIFT on z-score."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import httpx

from api.models.signal import Signal, SignalKind
from detectors.baseline import EwmaBaseline
from detectors.changepoint import PageHinkley

VM_URL = os.getenv("VM_URL", "http://victoria-metrics:8428")
# Soft absolute floor (ms) — used only until baseline has enough samples.
THRESHOLD_MS = float(os.getenv("DETECT_LATENCY_MS", "200"))
Z_THRESH = float(os.getenv("DETECT_Z", "3.0"))
MIN_SAMPLES = int(os.getenv("DETECT_MIN_SAMPLES", "3"))

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

_baselines: dict[str, EwmaBaseline] = {}
_changepoints: dict[str, PageHinkley] = {}


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


def _state(svc: str) -> tuple[EwmaBaseline, PageHinkley]:
    if svc not in _baselines:
        _baselines[svc] = EwmaBaseline(alpha=float(os.getenv("DETECT_EWMA_ALPHA", "0.1")))
    if svc not in _changepoints:
        _changepoints[svc] = PageHinkley(
            delta=float(os.getenv("DETECT_PH_DELTA", "0.005")),
            threshold=float(os.getenv("DETECT_PH_THRESH", "5.0")),
        )
    return _baselines[svc], _changepoints[svc]


async def detect_latency_signals() -> list[Signal]:
    now = datetime.now(timezone.utc)
    lat = await fetch_latency_by_service()
    signals: list[Signal] = []

    for svc, ms in lat.items():
        base, ph = _state(svc)
        z = base.update(ms)
        # Feed residual (or z) into Page-Hinkley for onset tracking.
        residual = ms - (base.mean if base.mean is not None else ms)
        changed = ph.update(residual, now)

        warm = base.n >= MIN_SAMPLES
        z_fire = warm and z >= Z_THRESH
        # Cold-start / safety net while EWMA warms up.
        abs_fire = (not warm) and ms > THRESHOLD_MS

        if not (z_fire or abs_fire):
            if ph.fired and z < Z_THRESH * 0.5:
                ph.reset()
            continue

        onset = ph.onset or now
        sev = min(1.0, max(0.4, abs(z) / 6.0 if warm else (ms - THRESHOLD_MS) / 800.0))
        signals.append(
            Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:16]}",
                kind=SignalKind.TRACE_LATENCY_SHIFT,
                node_id=f"svc:{svc}",
                severity=sev,
                onset_at=onset,
                observed_at=now,
                fingerprint=f"latency:{svc}",
                payload={
                    "service_name": svc,
                    "latency_ms": ms,
                    "z_score": round(z, 3),
                    "baseline_ms": round(base.mean or ms, 3),
                    "threshold_ms": THRESHOLD_MS,
                    "z_thresh": Z_THRESH,
                    "changepoint": changed or ph.fired,
                },
            )
        )
    return signals
