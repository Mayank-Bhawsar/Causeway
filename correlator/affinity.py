from datetime import datetime
from correlator.graph import adjacency, hop_distance

MAX_HOP = 4

def _dt(s: dict) -> datetime:
    from localiser.blame import _as_dt
    return _as_dt(s.get("onset_at") or s.get("observed_at"))

def pairwise_distance(signals: list[dict], edges: list[dict]) -> list[list[float]]:
    n = len(signals)
    g = adjacency(edges)
    dist = [[0.0] * n for _ in range(n)]
    t0 = min(_dt(s) for s in signals)

    for i in range(n):
        for j in range(i + 1, n):
            si, sj = signals[i], signals[j]
            # temporal: seconds apart, cap at 90s window
            dt = abs((_dt(si) - _dt(sj)).total_seconds()) / 90.0
            # graph hops
            hops = hop_distance(g, si["node_id"], sj["node_id"], MAX_HOP)
            if hops > MAX_HOP:
                graph_d = 1.0
            else:
                graph_d = hops / MAX_HOP
            # kind similarity
            kind_d = 0.0 if si.get("kind") == sj.get("kind") else 0.2
            d = 0.35 * min(dt, 1.0) + 0.55 * graph_d + 0.10 * kind_d
            dist[i][j] = dist[j][i] = d
    return dist