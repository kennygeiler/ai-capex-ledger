"""Statistics for the measured numbers (docs/EVALS.md, Statistics; docs/TICKETS.md T53): a share is never shown without
its denominator, and a share that is an estimate carries a Wilson 95% interval. Standard library only, pure functions."""
from __future__ import annotations

import math


def share(k: int, n: int) -> float | None:
    """k of n as a fraction, None when n == 0 (no denominator, no share)."""
    if n <= 0:
        return None
    return k / n


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """The Wilson score interval for a binomial share k of n at confidence z (1.96 = 95%), as (low, high) fractions.
    Wilson, E. B. (1927), "Probable inference, the law of succession, and statistical inference", JASA 22: 209–212.
    Unlike the normal approximation it stays inside [0, 1] and does not collapse to a point at k == 0 or k == n, so
    70 of 71 reads 0.924–0.998, not 0.986 ± 0.027. None when n == 0: there is no share to put an interval on."""
    if n <= 0:
        return None
    if k < 0 or k > n:
        raise ValueError(f"k must be within 0..n, got k={k}, n={n}")
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))
