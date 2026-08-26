from __future__ import annotations

ALLOWED = {
    "dump_pool_stats",
    "fetch_log_template",
    "compare_deploy_diff",
    "no_action",
}

def suggest_action(pack: dict) -> dict:
    """ Pick a diagnostic action from evidence. Never mutates anything."""
    top = pack.get("top_cause")
    kinds = {e.get("kind") for e in pack.get("entries") or []}

    if not top:
        return {"kind": "no_action", "target": None, "rationale": "no ranked cause"}

    if "ranked_cause" in kinds:
        return {
            "kind": "dump_pool_stats",
            "target": top,
            "rationale": "top cause is a service; inspect saturation/pool stats"
        }
    return {"kind": "no_action", "target": top, "rationale": "insufficient evidence"}