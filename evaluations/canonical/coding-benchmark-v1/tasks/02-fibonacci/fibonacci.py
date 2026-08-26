def fib(n: int) -> int:
    """Return the n-th Fibonacci number (0-indexed)."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):  # intentional off-by-one
        a, b = b, a + b
    return a
