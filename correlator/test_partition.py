from correlator.partition import split_clusters_by_graph


def test_dual_unrelated_splits_to_two_incidents():
    edges = [
        {"src": "svc:checkout-svc", "dst": "svc:payment-svc", "calls": 40, "call_share": 0.5},
        {"src": "svc:auth-svc", "dst": "svc:config-svc", "calls": 20, "call_share": 0.3},
    ]
    # One artificial mega-cluster (as if HDBSCAN over-merged).
    cluster = [
        {"node_id": "svc:payment-svc", "signal_id": "a"},
        {"node_id": "svc:checkout-svc", "signal_id": "b"},
        {"node_id": "svc:auth-svc", "signal_id": "c"},
        {"node_id": "svc:config-svc", "signal_id": "d"},
    ]
    parts = split_clusters_by_graph([cluster], edges)
    assert len(parts) == 2
    sizes = sorted(len(p) for p in parts)
    assert sizes == [2, 2]
