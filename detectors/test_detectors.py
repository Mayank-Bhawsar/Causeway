from detectors.baseline import EwmaBaseline
from detectors.changepoint import PageHinkley
from datetime import datetime, timezone


def test_ewma_fires_on_spike():
    b = EwmaBaseline(alpha=0.2)
    for x in [100.0, 102.0, 98.0, 101.0, 99.0]:
        z = b.update(x)
    assert abs(z) < 2.0
    z = b.update(400.0)
    assert z >= 3.0


def test_page_hinkley_records_onset():
    ph = PageHinkley(delta=0.01, threshold=2.0)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        assert ph.update(0.0, t0) is False
    t1 = datetime(2026, 9, 1, 12, 0, 10, tzinfo=timezone.utc)
    fired = False
    for i in range(20):
        if ph.update(5.0, t1):
            fired = True
            break
    assert fired
    assert ph.onset == t1


def test_page_hinkley_reset():
    ph = PageHinkley(delta=0.01, threshold=2.0)
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    for _ in range(5):
        ph.update(0.0, t0)
    t1 = datetime(2026, 9, 1, 12, 0, 10, tzinfo=timezone.utc)
    for _ in range(20):
        if ph.update(5.0, t1):
            break
    assert ph.fired
    ph.reset()
    assert ph.onset is None
    assert ph.fired is False
    assert ph.n == 0
