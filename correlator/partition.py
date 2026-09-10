"""Post-cluster split: separate signals with no graph path within MAX_HOP (Phase M1)."""
from __future__ import annotations

from correlator.graph import adjacency, hop_distance
from correlator.affinity import MAX_HOP


def _split_one_cluster(cluster: list[dict], edges: list[dict]) -> list[list[dict]]:
    n = len(cluster)
    if n <= 1:
        return [cluster]

    g = adjacency(edges)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            a = cluster[i]["node_id"]
            b = cluster[j]["node_id"]
            if hop_distance(g, a, b, MAX_HOP) <= MAX_HOP:
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pj] = pi

    buckets: dict[int, list[dict]] = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(cluster[i])
    return list(buckets.values())


def split_clusters_by_graph(
    clusters: list[list[dict]],
    edges: list[dict],
) -> list[list[dict]]:
    """Expand each cluster into graph-connected sub-clusters (one incident each)."""
    out: list[list[dict]] = []
    for cluster in clusters:
        out.extend(_split_one_cluster(cluster, edges))
    return out
