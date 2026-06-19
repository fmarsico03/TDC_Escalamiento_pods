import math


def clamp(value, lo, hi):
    """Acota value al intervalo [lo, hi]."""
    return max(lo, min(hi, value))


def ceil_to_nearest(value, base=10):
    """Redondea hacia arriba al múltiplo de base más cercano."""
    return base * math.ceil(value / base)
