def parse_csv_line(line: str) -> list[str]:
    """Split a simple CSV line on commas (no quoting support required)."""
    # intentional bug: strips empty trailing fields incorrectly
    return [part for part in line.split(",") if part]
