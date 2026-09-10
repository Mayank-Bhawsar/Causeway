"""Detect per-service call-rate spikes (overload proxy) from span call counts."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import httpx

from api.models.signal import Signal, SignalKind
from detectors.baseline import EwmaBaseline
from detectors.changepoint import PageHinkley

VM_URL = os.getenv("VM_URL", "http://victoria-metrics:8428")
Z_THRESH = float(os.getenv("DETECT_SAT_Z", "3.0"))
MIN_SAMPLES = int(os.getenv("DETECT_MIN_SAMPLES", "3"))
# Minimum calls per minute before saturation logic applies (cold start).
MIN_CALLS_PER_MIN = float(os.getenv("DETECT_SAT_MIN_CALLS", "5"))

QUERY = """
sum by (service_name) (
  increase(traces_span_metrics_calls_total{span_kind="SPAN_KIND_SERVER"}[1m])
)
"""

_baselines: dict[str, EwmaBaseline] = {}
_changepoints: dict[str, PageHinkley] = {}


async def fetch_calls_per_min_by_service() -> dict[str, float]:
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


async def detect_saturation_signals() -> list[Signal]:
    now = datetime.now(timezone.utc)
    try:
        rates = await fetch_calls_per_min_by_service()
    except Exception as exc:  # noqa: BLE001
        print(f"detect_saturation_signals query error: {exc}", flush=True)
        return []

    signals: list[Signal] = []
    for svc, cpm in rates.items():
        if cpm < MIN_CALLS_PER_MIN:
            continue
        base, ph = _state(svc)
        z = base.update(cpm)
        residual = cpm - (base.mean if base.mean is not None else cpm)
        changed = ph.update(residual, now)

        warm = base.n >= MIN_SAMPLES
        if not (warm and z >= Z_THRESH):
            if ph.fired and z < Z_THRESH * 0.5:
                ph.reset()
            continue

        onset = ph.onset or now
        sev = min(1.0, max(0.4, abs(z) / 6.0))
        signals.append(
            Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:16]}",
                kind=SignalKind.SATURATION,
                node_id=f"svc:{svc}",
                severity=sev,
                onset_at=onset,
                observed_at=now,
                fingerprint=f"saturation:{svc}",
                payload={
                    "service_name": svc,
                    "calls_per_min": round(cpm, 2),
                    "baseline_cpm": round(base.mean or cpm, 2),
                    "z_score": round(z, 3),
                    "z_thresh": Z_THRESH,
                    "changepoint": changed or ph.fired,
                },
            )
        )
    return signals
