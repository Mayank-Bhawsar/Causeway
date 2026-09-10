from pathlib import Path

from bench.replay import replay_fixture

FIXTURE = Path(__file__).parent / "fixtures" / "deploy_payment_rollout.json"


def test_deploy_plus_latency_top1():
    r = replay_fixture(FIXTURE)
    assert r["top1_ok"] is True
    assert r["top1"] == "svc:payment-svc"
