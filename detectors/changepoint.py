from __future__ import annotations

from datetime import datetime


class PageHinkley:
    """Online mean-shift detector; records first onset timestamp when fired."""

    def __init__(self, delta: float = 0.005, threshold: float = 5.0) -> None:
        self.mean = 0.0
        self.cum = 0.0
        self.min_cum = 0.0
        self.n = 0
        self.delta = delta
        self.threshold = threshold
        self.onset: datetime | None = None
        self.fired = False

    def update(self, x: float, t: datetime) -> bool:
        self.n += 1
        self.mean += (x - self.mean) / self.n
        self.cum += x - self.mean - self.delta
        self.min_cum = min(self.min_cum, self.cum)
        if self.cum - self.min_cum > self.threshold:
            if self.onset is None:
                self.onset = t
            self.fired = True
            return True
        return False

    def reset(self) -> None:
        self.mean = 0.0
        self.cum = 0.0
        self.min_cum = 0.0
        self.n = 0
        self.onset = None
        self.fired = False
