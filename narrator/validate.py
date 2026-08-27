from __future__ import annotations

import re
from typing import Any

EV_RE = re.compile(r"^EV-[A-Z]+-\d{4}$")
NUM_RE = re.compile(r"(?<![A-Za-z_])\d+(?:\.\d+)?")


def validate_narrative(pack: dict, body: dict) -> list[str]:
    """Return list of validation errors (empty = OK)."""
    errors: list[str] = []
    entries = pack.get("entries") or []
    keys = {e.get("key") for e in entries if e.get("key")}
    # flatten referenced evidence values for number checks
    value_blobs: dict[str, str] = {
        e["key"]: str(e) for e in entries if e.get("key")
    }
    nodes = set(pack.get("nodes") or [])
    for e in entries:
        if e.get("kind") == "topology_edge":
            nodes.add(e.get("src")); nodes.add(e.get("dst"))
        if e.get("node_id"):
            nodes.add(e["node_id"])

    for claim in body.get("claims") or []:
        refs = claim.get("evidence_refs") or []
        if not refs:
            errors.append(f"claim has zero evidence_refs: {claim.get('text')!r}")
        for ref in refs:
            if ref not in keys:
                errors.append(f"dangling evidence_ref {ref}")
        text = claim.get("text") or ""
        for num in NUM_RE.findall(text):
            ok = any(num in value_blobs.get(r, "") for r in refs)
            if not ok:
                errors.append(f"ungrounded number {num} in claim {text!r}")

    for cause in body.get("ranked_causes") or []:
        refs = cause.get("evidence_refs") or []
        if not refs:
            errors.append(f"cause {cause.get('node_id')} missing evidence_refs")
        for ref in refs:
            if ref not in keys:
                errors.append(f"dangling evidence_ref {ref} on cause")
        nid = cause.get("node_id")
        if nid and nodes and nid not in nodes:
            errors.append(f"node_id {nid} not in topology/signal set")

    action = body.get("suggested_action") or {}
    for ref in action.get("rationale_refs") or []:
        if ref not in keys:
            errors.append(f"dangling rationale_ref {ref}")

    return errors