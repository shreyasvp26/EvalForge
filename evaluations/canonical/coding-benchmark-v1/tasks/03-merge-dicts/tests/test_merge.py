from merge import merge


def test_merge_adds_keys() -> None:
    assert merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_right_wins() -> None:
    assert merge({"a": 1}, {"a": 9}) == {"a": 9}
