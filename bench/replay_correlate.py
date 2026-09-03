from correlator.affinity import pairwise_distance
from correlator.cluster import cluster_signals

def replay_correlate(path):
    fx = json.loads(path.read_text())
    dist = pairwise_distance(fx["signals"], fx.get("edges") or [])
    clusters = cluster_signals(fx["signals"], dist)
    return {
        "scenario": fx["scenario"],
        "clusters": len(clusters),
        "expected": fx.get("expected_incidents", 1),
        "ok": len(clusters) == fx.get("expected_incidents", 1),
    }