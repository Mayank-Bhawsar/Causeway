from __future__ import annotations


class EwmaBaseline:
    """Per-series EWMA mean/variance; returns residual z-score on each update."""

    def __init__(self, alpha: float = 0.1) -> None:
        self.mean: float | None = None
        self.var: float = 1.0
        self.alpha = alpha
        self.n: int = 0

    def update(self, x: float) -> float:
        self.n += 1
        if self.mean is None:
            self.mean = x
            return 0.0
        err = x - self.mean
        std = (self.var**0.5) + 1e-6
        self.mean += self.alpha * err
        self.var = (1.0 - self.alpha) * self.var + self.alpha * err * err
        return err / std
