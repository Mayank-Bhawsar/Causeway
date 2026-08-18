from __future__ import annotations

from collections import defaultdict


def rank_by_severity(signals: list[dict]) -> list[dict]:
    best: dict[str, float] = defaultdict(float)
    for s in signals:
        node = s["node_id"]
        sev = float(s.get("severity") or 0)
        if sev> best[node]:
            best[node]=sev
    ordered = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    out = []
    for i, (node_id, score) in enumerate(ordered, start=1):
        out.append(
            {
                "node_id": node_id,
                "rank": i,
                "score": score,
                "confidence": round(score, 3),
                "conformal_k": min(3, len(ordered)),
                "features": {"max_severity": score, "method": "naive_severity"},
            }
        )
    return out