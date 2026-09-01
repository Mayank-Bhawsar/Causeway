from __future__ import annotations

from typing import Any


def template_narrate(pack: dict[str, Any]) -> dict[str, Any]:
    """Deterministic narrative from evidence pack. Always passes validation."""
    entries = pack.get("entries") or []
    by_key = {e["key"]: e for e in entries if e.get("key")}

    ranked = [e for e in entries if e.get("kind") == "ranked_cause"]
    ranked.sort(key=lambda e: e.get("score") or 0, reverse=True)

    signals = [e for e in entries if e.get("kind") == "signal"]
    top = pack.get("top_cause") or (ranked[0]["node_id"] if ranked else None)

    ranked_causes = []
    for e in ranked[:3]:
        refs = [s["key"] for s in signals if s.get("node_id") == e.get("node_id")][:2]
        rca_key = e["key"]
        if rca_key not in refs:
            refs.insert(0, rca_key)
        ranked_causes.append({
            "node_id": e["node_id"],
            "why": f"Ranked by {e.get('method', 'localiser')} with score {e.get('score')}",
            "evidence_refs": refs[:4],
        })

    claims = []
    for s in signals[:3]:
        sev = s.get("severity")
        node = s.get("node_id", "unknown")
        claims.append({
            "text": f"Signal on {node} with severity {sev}",
            "evidence_refs": [s["key"]],
        })

    summary = (
        f"Incident {pack.get('incident_id')}: "
        f"{pack.get('signal_count', 0)} signals; top cause {top}."
    )

    return {
        "summary": summary,
        "ranked_causes": ranked_causes,
        "claims": claims,
        "uncertainty": "Template narrative — deterministic fallback, no LLM reasoning.",
    }