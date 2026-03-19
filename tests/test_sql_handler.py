from sql.sqlHandler import _normalize_name


def test_normalize_name_accepts_int_values():
    assert _normalize_name(12345) == "12345"


def test_normalize_name_returns_none_for_blank_strings():
    assert _normalize_name("   ") is None

from unittest.mock import MagicMock

from sql import sqlHandler


def test_upsert_seeds_by_year_accepts_division_alias():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    seed_rows = [{
        "team_id": 7,
        "seed": 3,
        "division": "South",
        "team_name": "Duke",
        "espn_id": 12345,
    }]

    original_get_connection = sqlHandler.getConnection
    try:
        sqlHandler.getConnection = lambda include_database=True: conn
        sqlHandler.upsertSeedsByYear(seed_rows, 2026)
    finally:
        sqlHandler.getConnection = original_get_connection

    insert_call = cursor.execute.call_args_list[-1]
    assert insert_call.args[1] == (7, 3, 1, 2026)
    conn.commit.assert_called_once()
