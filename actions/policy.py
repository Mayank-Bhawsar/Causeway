from __future__ import annotations

import os
from typing import Any

import httpx

from actions.suggest import ALLOWED


def _allowed_kinds() -> set[str]:
    raw = os.getenv(
        "ACTIONS_ALLOWED_KINDS",
        "dump_pool_stats,fetch_log_template,compare_deploy_diff,no_action",
    )
    return {k.strip() for k in raw.split(",") if k.strip()}


def evaluate_action(suggestion: dict[str, Any]) -> dict[str, Any]:
    """Local allowlist + optional OPA query. Does not execute anything."""
    kind = str(suggestion.get("kind") or "")
    if kind not in ALLOWED:
        return {
            "permitted": False,
            "reason": f"unknown action kind: {kind}",
            "suggestion": suggestion,
        }
    if kind not in _allowed_kinds():
        return {
            "permitted": False,
            "reason": f"{kind} blocked by ACTIONS_ALLOWED_KINDS",
            "suggestion": suggestion,
        }

    opa_url = os.getenv("OPA_URL", "").strip()
    if opa_url:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(
                    f"{opa_url.rstrip('/')}/v1/data/causeway/action/allow",
                    json={"input": {"action": suggestion}},
                )
                r.raise_for_status()
                allowed = bool(r.json().get("result"))
                return {
                    "permitted": allowed,
                    "reason": "opa" if allowed else "opa denied",
                    "suggestion": suggestion,
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "permitted": False,
                "reason": f"opa error: {exc}",
                "suggestion": suggestion,
            }

    return {"permitted": True, "reason": "local allowlist", "suggestion": suggestion}
