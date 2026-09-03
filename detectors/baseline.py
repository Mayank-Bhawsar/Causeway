# detectors/baseline.py
class EwmaBaseline:
    def __init__(self, alpha=0.1):
        self.mean = None
        self.var = 1.0
        self.alpha = alpha

    def update(self, x: float) -> float:
        if self.mean is None:
            self.mean = x
            return 0.0
        err = x - self.mean
        self.mean += self.alpha * err
        self.var = (1 - self.alpha) * self.var + self.alpha * err * err
        z = err / (self.var ** 0.5 + 1e-6)
        return z  # fire if z > ~3