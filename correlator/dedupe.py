from __future__ import annotations

from datetime import datetime, timezone

from localiser.blame import _as_dt

# Same service + latency-related kinds collapse to one slot in the correlator window.
_LATENCY_KINDS = frozenset({"alert", "trace_latency_shift"})
_ERROR_KINDS = frozenset({"trace_error_shift"})


def dedupe_key(signal: dict) -> str:
    node = signal.get("node_id") or ""
    kind = str(signal.get("kind") or "")
    if kind in _LATENCY_KINDS:
        return f"anomaly:latency:{node}"
    if kind in _ERROR_KINDS:
        return f"anomaly:error:{node}"
    fp = signal.get("fingerprint")
    if fp:
        return str(fp)
    return f"{kind}:{node}:{signal.get('signal_id')}"


def _merge_pair(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    out["severity"] = max(float(existing.get("severity") or 0), float(incoming.get("severity") or 0))

    t_old = _as_dt(existing.get("onset_at") or existing.get("observed_at"))
    t_new = _as_dt(incoming.get("onset_at") or incoming.get("observed_at"))
    if t_old and t_new:
        out["onset_at"] = (t_old if t_old <= t_new else t_new).isoformat()
    elif t_new:
        out["onset_at"] = incoming.get("onset_at") or incoming.get("observed_at")

    o_old = _as_dt(existing.get("observed_at"))
    o_new = _as_dt(incoming.get("observed_at"))
    if o_old and o_new:
        out["observed_at"] = (o_old if o_old >= o_new else o_new).isoformat()
    else:
        out["observed_at"] = incoming.get("observed_at") or existing.get("observed_at")

    payload = dict(existing.get("payload") or {})
    payload.update(incoming.get("payload") or {})
    out["payload"] = payload
    if existing.get("kind") == "trace_latency_shift" or incoming.get("kind") == "trace_latency_shift":
        out["kind"] = "trace_latency_shift"
    else:
        out["kind"] = existing.get("kind") or incoming.get("kind")
    return out


def merge_into_buffer(buf: list[dict], incoming: dict) -> tuple[dict, bool]:
    """Return (signal to persist, True if merged into an existing row)."""
    key = dedupe_key(incoming)
    for i, existing in enumerate(buf):
        if dedupe_key(existing) == key:
            merged = _merge_pair(existing, incoming)
            buf[i] = merged
            return merged, True
    buf.append(incoming)
    return incoming, False
