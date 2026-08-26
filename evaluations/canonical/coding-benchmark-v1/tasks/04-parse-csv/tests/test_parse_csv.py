from parse_csv import parse_csv_line


def test_basic() -> None:
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_empty_fields() -> None:
    assert parse_csv_line("a,,c") == ["a", "", "c"]
    assert parse_csv_line("a,b,") == ["a", "b", ""]
