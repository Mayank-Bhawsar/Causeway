from __future__ import annotations

import numpy as np
from sklearn.cluster import HDBSCAN


def cluster_signals(signals: list[dict], dist: list[list[float]]) -> list[list[dict]]:
    """Cluster signals from a precomputed distance matrix.

    Runs Union-Find on pairs with dist < 0.95, then HDBSCAN per component.
    If HDBSCAN labels everything as noise, keep the whole component as one cluster.
    """
    n = len(signals)
    if n == 0:
        return []
    if n <= 1:
        return [signals]

    D = np.array(dist, dtype=float)
    np.fill_diagonal(D, 0.0)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if D[i, j] < 0.95:
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pj] = pi

    comps: dict[int, list[int]] = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)

    clusters: list[list[dict]] = []
    for idxs in comps.values():
        sub = [signals[i] for i in idxs]
        if len(sub) == 1:
            clusters.append(sub)
            continue
        if len(sub) == 2:
            # HDBSCAN needs min_cluster_size=2; treat pair as one cluster.
            clusters.append(sub)
            continue

        subD = D[np.ix_(idxs, idxs)]
        labels = HDBSCAN(
            metric="precomputed", min_cluster_size=2, copy=True
        ).fit_predict(subD)
        if all(int(lab) == -1 for lab in labels):
            clusters.append(sub)
            continue

        buckets: dict[int, list[dict]] = {}
        for lab, sig in zip(labels, sub, strict=True):
            buckets.setdefault(int(lab), []).append(sig)
        for lab, grp in buckets.items():
            if lab == -1:
                for s in grp:
                    clusters.append([s])
            else:
                clusters.append(grp)
    return clusters
