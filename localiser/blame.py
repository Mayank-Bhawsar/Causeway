from __future__ import annotations

from collections import defaultdict


def _pagerank(
    nodes: list[str],
    out_edges: dict[str, list[tuple[str, float]]],
    personalization: dict[str, float],
    damping: float = 0.85,
    iters: int = 40,
) -> dict[str,float]:
    n = len(nodes)
    if n == 0:
        return {}
    pr = {u: 1.0 / n for u in nodes}
    psum = sum(personalization.get(u,0.0) for u in nodes) or 1.0
    pers = {u: personalization.get(u,0.0) / psum for u in nodes}

    for _ in range(iters):
        nxt = {u: (1.0 - damping) * pers[u] for u in nodes}
        for u in nodes:
            outs = out_edges.get(u) or []
            if not outs:
                for v in nodes:
                    nxt[v] +=damping * pr[u] * pers[v]
                continue
            wsum = sum(w for _, w in outs) or 1.0
            for v,w in outs:
                nxt[v] += damping * pr[u] * (w / wsum)
        pr = nxt
    return pr

def rank_by_blame(
    signals: list[dict],
    edges: list[dict]
) -> list[dict]:
    sev: dict[str, float] = defaultdict(float)
    for s in signals:
        node = s["node_id"]
        sev[node] = max(sev[node], float(s.get("severity") or 0.0))

    if not edges:
        return []

    nodes = sorted({e["src"] for e in edges} | {e["dst"] for e in edges} | set(sev))

    out: dict[str, list[tuple[str,float]]] = defaultdict(list)

    for e in edges:
        w = float(e.get("call_share") or e.get("calls") or 1.0)
        out[e["src"]].append((e["dst"],w))
        out[e["dst"]].append((e["src"], 0.25 * w))

    for u in nodes:
        has_forward = any(e["src"] == u for e in edges)
        if not has_forward or not out[u]:
            out[u].append((u, 1.0))

    pers = {u: sev.get(u, 0.0) for u in nodes}
    if sum(pers.values()) <=0:
        pers = {u: 1.0 for u in nodes}

    raw = _pagerank(nodes, out, pers)
    base = _pagerank(nodes, out, {u: 1.0 for u in nodes})
    lift = {
        u: (raw[u] / base[u]) if base.get(u,0) > 1e-12 else raw[u]
        for u in nodes
        if sev.get(u, 0) > 0
    }
    ordered = sorted(lift.items(), key=lambda kv: kv[1], reverse=True)
    return [
        {
            "node_id": node_id,
            "rank": i,
            "score": float(score),
            "confidence": round(min(1.0, float(score) / (ordered[0][1] or 1.0)), 3),
            "conformal_k": min(3, len(ordered)),
            "features": {
                "method": "blame_pagerank",
                "ppr_raw": raw.get(node_id, 0.0),
                "ppr_base": base.get(node_id, 0.0),
                "max_severity": sev.get(node_id, 0.0),
            },
        }
        for i, (node_id, score) in enumerate(ordered, start=1)
    ]

        
        