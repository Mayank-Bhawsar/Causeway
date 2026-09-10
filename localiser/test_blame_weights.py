from localiser.blame import _blame_weights


def test_blame_weights_defaults():
    sev, onset, sec = _blame_weights()
    assert sev == 1.0
    assert onset == 1.0
    assert sec == 60.0


def test_blame_weights_from_env(monkeypatch):
    monkeypatch.setenv("BLAME_SEV_WEIGHT", "1.5")
    monkeypatch.setenv("BLAME_ONSET_WEIGHT", "2.0")
    monkeypatch.setenv("BLAME_ONSET_SEC", "30")
    sev, onset, sec = _blame_weights()
    assert sev == 1.5
    assert onset == 2.0
    assert sec == 30.0
