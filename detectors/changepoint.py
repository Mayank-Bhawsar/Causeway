# detectors/changepoint.py
class PageHinkley:
    def __init__(self, delta=0.01, threshold=50):
        self.mean = 0.0; self.cum = 0.0; self.min_cum = 0.0
        self.n = 0; self.delta = delta; self.threshold = threshold
        self.onset = None

    def update(self, x, t):
        self.n += 1
        self.mean += (x - self.mean) / self.n
        self.cum += x - self.mean - self.delta
        self.min_cum = min(self.min_cum, self.cum)
        if self.cum - self.min_cum > self.threshold:
            self.onset = self.onset or t
            return True  # change detected
        return False