from actions.policy import evaluate_action


def test_dump_pool_stats_allowed_by_default():
    s = {"kind": "dump_pool_stats", "target": "svc:payment-svc", "rationale": "test"}
    out = evaluate_action(s)
    assert out["permitted"] is True


def test_unknown_kind_blocked():
    out = evaluate_action({"kind": "restart_pod", "target": "svc:x"})
    assert out["permitted"] is False
