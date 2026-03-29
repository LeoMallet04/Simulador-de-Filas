# metodo congruente linear
class RandomGenerator:
    def __init__(self, seed: int, a: int = 1664525, c: int = 1013904223, M: int = 2**32):
        self.previous = seed
        self.a = a
        self.c = c
        self.M = M
        self.count = 0

    def next_random(self) -> float:
        """Retorna número pseudoaleatório normalizado [0, 1)"""

        self.previous = (self.a * self.previous + self.c) % self.M
        self.count += 1
        return self.previous / self.M

    def rand_between(self, low: float, high: float) -> float:
        """Retorna número uniformemente distribuído entre [low, high]"""

        return low + self.next_random() * (high - low)
