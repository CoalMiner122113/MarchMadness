from sql.sqlHandler import _normalize_name


def test_normalize_name_accepts_int_values():
    assert _normalize_name(12345) == "12345"


def test_normalize_name_returns_none_for_blank_strings():
    assert _normalize_name("   ") is None
