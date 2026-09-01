from __future__ import annotations
from collections import deque, defaultdict

def adjacency(edges: list[dict]) -> dict[str, set[str]]:
    g: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        g[e["src"]].add(e["dst"])
        g[e["dst"]].add(e["src"])  # undirected for "relatedness"
    return g

def hop_distance(g: dict[str, set[str]], a: str, b: str, max_hop: int = 4) -> int:
    if a == b:
        return 0
    if a not in g or b not in g:
        return max_hop + 1
    seen = {a}
    q = deque([(a, 0)])
    while q:
        u, d = q.popleft()
        if d >= max_hop:
            continue
        for v in g[u]:
            if v == b:
                return d + 1
            if v not in seen:
                seen.add(v)
                q.append((v, d + 1))
    return max_hop + 1