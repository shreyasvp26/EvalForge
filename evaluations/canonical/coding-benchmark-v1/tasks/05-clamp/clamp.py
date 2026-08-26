def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value into the inclusive range [lo, hi]."""
    # intentional bug: ignores upper bound
    if value < lo:
        return lo
    return value
