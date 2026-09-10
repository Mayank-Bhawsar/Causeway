"""Saturation: call-rate spikes (span metrics) + mesh fault flag (meshgen_fault_active)."""

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
MIN_CALLS_PER_MIN = float(os.getenv("DETECT_SAT_MIN_CALLS", "5"))
FAULT_SEV = float(os.getenv("DETECT_FAULT_SEV", "0.85"))

CALLS_QUERY = """
sum by (service_name) (
  increase(traces_span_metrics_calls_total{span_kind="SPAN_KIND_SERVER"}[1m])
)
"""

FAULT_QUERY = "meshgen_fault_active == 1"

_baselines: dict[str, EwmaBaseline] = {}
_changepoints: dict[str, PageHinkley] = {}
_fault_since: dict[str, datetime] = {}


async def _vm_query(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{VM_URL}/api/v1/query", params={"query": query})
        r.raise_for_status()
        return r.json().get("data", {}).get("result") or []


async def fetch_calls_per_min_by_service() -> dict[str, float]:
    out: dict[str, float] = {}
    for row in await _vm_query(CALLS_QUERY):
        svc = row["metric"].get("service_name")
        if svc:
            out[svc] = float(row["value"][1])
    return out


async def fetch_active_faults_by_service() -> dict[str, float]:
    """Services with meshgen_fault_active gauge set (from vmagent scrape)."""
    out: dict[str, float] = {}
    for row in await _vm_query(FAULT_QUERY):
        svc = row["metric"].get("service")
        if not svc:
            continue
        out[svc] = float(row["value"][1])
    return out


def build_fault_active_signals(
    faults: dict[str, float],
    now: datetime,
    fault_since: dict[str, datetime],
) -> list[Signal]:
    signals: list[Signal] = []
    active = {svc for svc, v in faults.items() if v >= 0.5}

    for svc in list(fault_since):
        if svc not in active:
            del fault_since[svc]

    for svc in active:
        if svc not in fault_since:
            fault_since[svc] = now
        onset = fault_since[svc]
        signals.append(
            Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:16]}",
                kind=SignalKind.SATURATION,
                node_id=f"svc:{svc}",
                severity=FAULT_SEV,
                onset_at=onset,
                observed_at=now,
                fingerprint=f"fault_active:{svc}",
                payload={
                    "service_name": svc,
                    "fault_active": 1,
                    "source": "meshgen_fault_active",
                    "reason": "injected_fault_or_cpu_burn",
                },
            )
        )
    return signals


def _state(svc: str) -> tuple[EwmaBaseline, PageHinkley]:
    if svc not in _baselines:
        _baselines[svc] = EwmaBaseline(alpha=float(os.getenv("DETECT_EWMA_ALPHA", "0.1")))
    if svc not in _changepoints:
        _changepoints[svc] = PageHinkley(
            delta=float(os.getenv("DETECT_PH_DELTA", "0.005")),
            threshold=float(os.getenv("DETECT_PH_THRESH", "5.0")),
        )
    return _baselines[svc], _changepoints[svc]


def _call_rate_signals(rates: dict[str, float], now: datetime) -> list[Signal]:
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
                fingerprint=f"saturation_cpm:{svc}",
                payload={
                    "service_name": svc,
                    "calls_per_min": round(cpm, 2),
                    "baseline_cpm": round(base.mean or cpm, 2),
                    "z_score": round(z, 3),
                    "z_thresh": Z_THRESH,
                    "source": "span_call_rate",
                    "changepoint": changed or ph.fired,
                },
            )
        )
    return signals


async def detect_saturation_signals() -> list[Signal]:
    now = datetime.now(timezone.utc)
    signals: list[Signal] = []

    try:
        faults = await fetch_active_faults_by_service()
        signals.extend(build_fault_active_signals(faults, now, _fault_since))
    except Exception as exc:  # noqa: BLE001
        print(f"detect_saturation fault_active error: {exc}", flush=True)

    try:
        rates = await fetch_calls_per_min_by_service()
        signals.extend(_call_rate_signals(rates, now))
    except Exception as exc:  # noqa: BLE001
        print(f"detect_saturation call_rate error: {exc}", flush=True)

    return signals
