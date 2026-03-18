"""Tests for app_logic/import_brackets.py."""

import pytest

from app_logic.import_brackets import (
    GAME_COUNTS,
    REQUIRED_GAME_FIELDS,
    ROUND_NAMES,
    _deduplicate_name,
    prepare_bracket,
    validate_bracket,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(team1: str = "TeamA", team2: str = "TeamB", winner: str = "TeamA") -> dict:
    """Return a minimal valid game dict."""
    return {
        "division": "South",
        "team1": team1,
        "team2": team2,
        "winner": winner,
        "loser": team2 if winner == team1 else team1,
        "winner_espn_probability": 0.6,
        "winner_kenpom_probability": 0.62,
        "winner_simulation_probability": 0.61,
        "winner_moneyline": -150,
    }


def _make_valid_results() -> dict:
    """Build a results dict with the correct game count per round."""
    results: dict = {}
    for round_name, count in GAME_COUNTS.items():
        results[round_name] = [_make_game() for _ in range(count)]
    return results


def _make_valid_bracket() -> dict:
    """Return a fully valid bracket dict."""
    results = _make_valid_results()
    results["Championship"][0]["winner"] = "TeamA"
    results["Championship"][0]["loser"] = "TeamB"
    return {
        "id": "bracket_aabbccddee",
        "name": "Test Bracket",
        "saved_at": "2026-03-17T12:00:00+00:00",
        "year": 2026,
        "source": "kenpom",
        "default_probability_source": "ESPN Probability",
        "champion": "TeamA",
        "results": results,
        "upset_counts": {"Round of 64": 2},
        "seeding": [],
    }


# ---------------------------------------------------------------------------
# validate_bracket
# ---------------------------------------------------------------------------

def test_validate_accepts_well_formed_bracket() -> None:
    errors = validate_bracket(_make_valid_bracket())
    assert errors == []


def test_validate_rejects_non_dict_top_level() -> None:
    errors = validate_bracket([])  # type: ignore[arg-type]
    assert errors


def test_validate_rejects_missing_results() -> None:
    bracket = _make_valid_bracket()
    del bracket["results"]
    errors = validate_bracket(bracket)
    assert any("results" in e for e in errors)


def test_validate_rejects_results_not_dict() -> None:
    bracket = _make_valid_bracket()
    bracket["results"] = "not a dict"
    errors = validate_bracket(bracket)
    assert errors


def test_validate_rejects_missing_round() -> None:
    bracket = _make_valid_bracket()
    del bracket["results"]["Sweet 16"]
    errors = validate_bracket(bracket)
    assert any("Sweet 16" in e for e in errors)


def test_validate_rejects_wrong_game_count_low() -> None:
    bracket = _make_valid_bracket()
    bracket["results"]["Round of 64"].pop()  # 31 instead of 32
    errors = validate_bracket(bracket)
    assert any("Round of 64" in e and "32" in e for e in errors)


def test_validate_rejects_wrong_game_count_high() -> None:
    bracket = _make_valid_bracket()
    bracket["results"]["Championship"].append(_make_game())  # 2 instead of 1
    errors = validate_bracket(bracket)
    assert any("Championship" in e for e in errors)


def test_validate_rejects_missing_game_field() -> None:
    bracket = _make_valid_bracket()
    del bracket["results"]["Elite 8"][0]["winner"]
    errors = validate_bracket(bracket)
    assert any("Elite 8" in e and "winner" in e for e in errors)


def test_validate_rejects_winner_not_team() -> None:
    bracket = _make_valid_bracket()
    bracket["results"]["Final Four"][0]["winner"] = "SomeOtherTeam"
    errors = validate_bracket(bracket)
    assert any("Final Four" in e and "winner" in e for e in errors)


def test_validate_allows_missing_optional_fields() -> None:
    bracket = _make_valid_bracket()
    for key in ("seeding", "upset_counts", "source", "saved_at", "year",
                "default_probability_source"):
        bracket.pop(key, None)
    errors = validate_bracket(bracket)
    assert errors == []


def test_validate_flags_champion_mismatch() -> None:
    bracket = _make_valid_bracket()
    bracket["champion"] = "WrongTeam"
    errors = validate_bracket(bracket)
    assert any("champion" in e.lower() for e in errors)


def test_validate_ok_when_champion_absent() -> None:
    """No champion key — no cross-check error, just accept."""
    bracket = _make_valid_bracket()
    del bracket["champion"]
    errors = validate_bracket(bracket)
    assert errors == []


# ---------------------------------------------------------------------------
# _deduplicate_name
# ---------------------------------------------------------------------------

def test_deduplicate_no_conflict() -> None:
    assert _deduplicate_name("Alpha", ["Beta", "Gamma"]) == "Alpha"


def test_deduplicate_single_conflict() -> None:
    assert _deduplicate_name("Alpha", ["Alpha"]) == "Alpha (1)"


def test_deduplicate_chain() -> None:
    assert _deduplicate_name("Alpha", ["Alpha", "Alpha (1)"]) == "Alpha (2)"


def test_deduplicate_long_chain() -> None:
    existing = ["Alpha"] + [f"Alpha ({i})" for i in range(1, 5)]
    assert _deduplicate_name("Alpha", existing) == "Alpha (5)"


# ---------------------------------------------------------------------------
# prepare_bracket
# ---------------------------------------------------------------------------

def test_prepare_strips_json_extension() -> None:
    bracket = prepare_bracket(_make_valid_bracket(), "My_Bracket.json", [])
    assert bracket["name"] == "My_Bracket"


def test_prepare_no_extension_unchanged() -> None:
    bracket = prepare_bracket(_make_valid_bracket(), "My_Bracket", [])
    assert bracket["name"] == "My_Bracket"


def test_prepare_deduplicates_name() -> None:
    bracket = prepare_bracket(_make_valid_bracket(), "foo.json", ["foo"])
    assert bracket["name"] == "foo (1)"


def test_prepare_deduplicates_name_chain() -> None:
    bracket = prepare_bracket(_make_valid_bracket(), "foo.json", ["foo", "foo (1)"])
    assert bracket["name"] == "foo (2)"


def test_prepare_generates_new_id() -> None:
    data = _make_valid_bracket()
    original_id = data["id"]
    bracket = prepare_bracket(data, "test.json", [])
    assert bracket["id"] != original_id
    assert bracket["id"].startswith("bracket_")


def test_prepare_preserves_results() -> None:
    data = _make_valid_bracket()
    bracket = prepare_bracket(data, "test.json", [])
    assert bracket["results"] is data["results"]


def test_prepare_defaults_upset_counts_when_missing() -> None:
    data = _make_valid_bracket()
    del data["upset_counts"]
    bracket = prepare_bracket(data, "test.json", [])
    assert bracket["upset_counts"] == {}


def test_prepare_preserves_upset_counts_when_present() -> None:
    data = _make_valid_bracket()
    data["upset_counts"] = {"Round of 64": 5}
    bracket = prepare_bracket(data, "test.json", [])
    assert bracket["upset_counts"] == {"Round of 64": 5}


def test_prepare_derives_champion_from_results() -> None:
    data = _make_valid_bracket()
    del data["champion"]
    data["results"]["Championship"][0]["winner"] = "TeamA"
    bracket = prepare_bracket(data, "test.json", [])
    assert bracket["champion"] == "TeamA"


def test_prepare_defaults_seeding_when_missing() -> None:
    data = _make_valid_bracket()
    del data["seeding"]
    bracket = prepare_bracket(data, "test.json", [])
    assert bracket["seeding"] == []
