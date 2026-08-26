from clamp import clamp


def test_inside() -> None:
    assert clamp(5, 0, 10) == 5


def test_below() -> None:
    assert clamp(-1, 0, 10) == 0


def test_above() -> None:
    assert clamp(99, 0, 10) == 10
