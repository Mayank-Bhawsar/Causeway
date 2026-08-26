from __future__ import annotations

from datetime import datetime, timezone

def build_stub_pack(
    incident_id: str,
    win_start: datetime,
    win_end: datetime,
    signals: list[dict],
    candidates: list[dict],
) -> dict:
    entries: list[dict] = []
    n=1

    for s in signals:
        entries.append({
            "key":f"EV-SIG-{n:04d}",
            "kind": "signal",
            "node_id": s["node_id"],
            "signal_kind": s["kind"],
            "severity": s.get("severity"),
            "payload": s.get("payload") or {},
        })
        n+=1

    for c in candidates:
        entries.append({
            "key": f"EV-RCA-{c['rank']:04d}",
            "kind": "ranked_cause",
            "node_id": c["node_id"],
            "score": c["score"],
            "method": c.get("features", {}).get("method", "naive_severity"),
        })

    return {
        "incident_id": incident_id,
        "version": "stub-v1",
        "window": {
            "start": win_start.isoformat(),
            "end": win_end.isoformat(),
        },
        "signal_count": len(signals),
        "entries": entries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_evidence_pack(
    incident_id: str,
    win_start,
    win_end,
    signals: list[dict],
    candidates: list[dict],
    edges: list[dict] | None = None,
) -> dict:
    entries = []
    n = 1

    for s in signals:
        entries.append({
            "key": f"EV-SIG-{n:04d}",
            "kind": "signal",
            "node_id": s["node_id"],
            "signal_kind": s["kind"],
            "severity": s.get("severity"),
            "onset_at": s.get("onset_at") or s.get("observed_at"),
            "payload": s.get("payload") or {},
        })
        n+=1

    for c in candidates[:5]:
        entries.append({
            "key": f"EV-RCA-{c['rank']:04d}",
            "kind": "ranked_cause",
            "node_id": c["node_id"],
            "score": c["score"],
            "confidence": c.get("confidence"),
            "method": (c.get("features") or {}).get("method"),
        })

    hot = {s["node_id"] for s in signals} | {c["node_id"] for c in candidates[:5]}
    topo =[]
    for e in edges or []:
        if e["src"] in hot or e["dst"] in hot:
            topo.append({
                "key": f"EV-TOPO-{len(topo):04d}",
                "kind": "topology_edge",
                "src": e["src"],
                "dst": e["dst"],
                "calls": e.get("calls"),
                "call_share": e.get("call_share"),
            })
    entries.extend(topo)

    return {
        "incident_id": incident_id,
        "version": "v1",
        "window": {"start": win_start.isoformat(), "end": win_end.isoformat()},
        "signal_count": len(signals),
        "top_cause": candidates[0]["node_id"] if candidates else None,
        "entries": entries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }