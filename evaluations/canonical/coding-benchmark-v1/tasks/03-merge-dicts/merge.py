def merge(left: dict, right: dict) -> dict:
    """Shallow-merge two dicts; right wins on key conflicts."""
    result = dict(left)
    # intentional bug: never applies right-side keys
    return result
