"""Poll VM for per-service error ratio; emit TRACE_ERROR_SHIFT on z-score."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import httpx

from api.models.signal import Signal, SignalKind
from detectors.baseline import EwmaBaseline
from detectors.changepoint import PageHinkley

VM_URL = os.getenv("VM_URL", "http://victoria-metrics:8428")
Z_THRESH = float(os.getenv("DETECT_ERROR_Z", "3.0"))
MIN_SAMPLES = int(os.getenv("DETECT_MIN_SAMPLES", "3"))
# Absolute floor while baseline warms (fraction of requests that are errors).
ABS_FLOOR = float(os.getenv("DETECT_ERROR_FLOOR", "0.15"))

# status_code is a default spanmetrics dimension in otel contrib.
QUERY = """
(
  sum by (service_name) (
    increase(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[1m])
  )
  /
  clamp_min(
    sum by (service_name) (
      increase(traces_span_metrics_calls_total[1m])
    ),
    1
  )
)
"""

_baselines: dict[str, EwmaBaseline] = {}
_changepoints: dict[str, PageHinkley] = {}


async def fetch_error_ratio_by_service() -> dict[str, float]:
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


async def detect_error_signals() -> list[Signal]:
    now = datetime.now(timezone.utc)
    try:
        ratios = await fetch_error_ratio_by_service()
    except Exception as exc:  # noqa: BLE001
        print(f"detect_error_signals query error: {exc}", flush=True)
        return []

    signals: list[Signal] = []
    for svc, ratio in ratios.items():
        base, ph = _state(svc)
        z = base.update(ratio)
        residual = ratio - (base.mean if base.mean is not None else ratio)
        changed = ph.update(residual, now)

        warm = base.n >= MIN_SAMPLES
        z_fire = warm and z >= Z_THRESH
        abs_fire = (not warm) and ratio >= ABS_FLOOR

        if not (z_fire or abs_fire):
            if ph.fired and z < Z_THRESH * 0.5:
                ph.reset()
            continue

        onset = ph.onset or now
        sev = min(1.0, max(0.4, abs(z) / 6.0 if warm else ratio))
        signals.append(
            Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:16]}",
                kind=SignalKind.TRACE_ERROR_SHIFT,
                node_id=f"svc:{svc}",
                severity=sev,
                onset_at=onset,
                observed_at=now,
                fingerprint=f"error:{svc}",
                payload={
                    "service_name": svc,
                    "error_ratio": round(ratio, 4),
                    "z_score": round(z, 3),
                    "baseline_ratio": round(base.mean or ratio, 4),
                    "z_thresh": Z_THRESH,
                    "changepoint": changed or ph.fired,
                },
            )
        )
    return signals
