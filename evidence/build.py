from __future__ import annotations

from datetime import datetime, timezone

def build_stub_pack(
    incident_id: str,
    win_start: datetime,
    win_end: datetime,
    signals: list[dict],
    candidate: list[dict],
) -> dict:
    entries: list[dict] = []
    n=1

    for s in signals:
        entries.append({
            "key":f"EV-SIG-n{n:04d}",
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
        