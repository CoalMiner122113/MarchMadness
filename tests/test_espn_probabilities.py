import os
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scraping.espnConnect import ESPNConnect


@pytest.fixture
def client():
    return ESPNConnect()


def _competitor(team_id, display_name, **extra):
    row = {
        "team": {
            "id": str(team_id),
            "displayName": display_name,
        }
    }
    row.update(extra)
    return row


def _event(event_id, competitors=None, probabilities=None, odds=None):
    competition = {
        "competitors": competitors or [],
    }
    if probabilities is not None:
        competition["probabilities"] = probabilities
    if odds is not None:
        competition["odds"] = odds
    return {
        "id": str(event_id),
        "competitions": [competition],
    }


def _mock_payload(monkeypatch, client, payload):
    monkeypatch.setattr(client, "_get_json", lambda path, params=None: payload)


def test_fetch_matchup_probabilities_uses_competition_probabilities(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1001,
                competitors=[
                    _competitor("1", "Alpha"),
                    _competitor("2", "Beta"),
                ],
                probabilities=[
                    {"team": {"id": "1"}, "value": 63.4},
                    {"team": {"id": "2"}, "value": 36.6},
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows == [
        {
            "team1": "Alpha",
            "team2": "Beta",
            "team1_probability": 63.4,
            "team1_moneyline": None,
            "team2_moneyline": None,
            "event_id": "1001",
        }
    ]


def test_fetch_matchup_probabilities_falls_back_to_competitor_probability(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1002,
                competitors=[
                    _competitor("1", "Alpha", probability=57.25),
                    _competitor("2", "Beta"),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_probability"] == 57.25


@pytest.mark.parametrize("field_name", ["probability", "winProbability", "chanceToWin"])
def test_fetch_matchup_probabilities_supports_all_fallback_fields(monkeypatch, client, field_name):
    payload = {
        "events": [
            _event(
                1003,
                competitors=[
                    _competitor("1", "Alpha", **{field_name: 58.0}),
                    _competitor("2", "Beta"),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_probability"] == 58.0


def test_fetch_matchup_probabilities_converts_zero_to_one_scale_to_percent(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1004,
                competitors=[
                    _competitor("1", "Alpha", winProbability=0.62),
                    _competitor("2", "Beta"),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_probability"] == 62.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-20, 0.0), (140, 100.0)],
)
def test_fetch_matchup_probabilities_clamps_out_of_range_values(monkeypatch, client, value, expected):
    payload = {
        "events": [
            _event(
                1005,
                competitors=[
                    _competitor("1", "Alpha", probability=value),
                    _competitor("2", "Beta"),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_probability"] == expected


@pytest.mark.parametrize(
    "competitors",
    [[], [_competitor("1", "Alpha")]],
)
def test_fetch_matchup_probabilities_ignores_events_with_too_few_competitors(monkeypatch, client, competitors):
    payload = {"events": [_event(1006, competitors=competitors)]}
    _mock_payload(monkeypatch, client, payload)

    assert client.fetch_matchup_probabilities(2026) == []


@pytest.mark.parametrize(
    "display_names",
    [("", "Beta"), ("Alpha", ""), (None, "Beta")],
)
def test_fetch_matchup_probabilities_ignores_missing_team_names(monkeypatch, client, display_names):
    name1, name2 = display_names
    payload = {
        "events": [
            _event(
                1007,
                competitors=[
                    _competitor("1", name1),
                    _competitor("2", name2),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    assert client.fetch_matchup_probabilities(2026) == []


def test_fetch_matchup_probabilities_ignores_events_without_usable_probability(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1008,
                competitors=[
                    _competitor("1", "Alpha", probability="bad"),
                    _competitor("2", "Beta"),
                ],
                probabilities=[
                    {"team": {"id": "1"}, "value": "not-a-number"},
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    assert client.fetch_matchup_probabilities(2026) == []


def test_fetch_matchup_probabilities_matches_probability_by_team_id(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1009,
                competitors=[
                    _competitor("10", "Alpha"),
                    _competitor("20", "Beta"),
                ],
                probabilities=[
                    {"team": {"id": "20"}, "value": 22.0},
                    {"team": {"id": "10"}, "value": 78.0},
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_probability"] == 78.0


def test_fetch_matchup_probabilities_skips_invalid_rows_but_keeps_valid_rows(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1010,
                competitors=[
                    _competitor("1", "Alpha", probability="bad"),
                    _competitor("2", "Beta"),
                ],
            ),
            _event(
                1011,
                competitors=[
                    _competitor("3", "Gamma", probability=55.5),
                    _competitor("4", "Delta"),
                ],
            ),
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows == [
        {
            "team1": "Gamma",
            "team2": "Delta",
            "team1_probability": 55.5,
            "team1_moneyline": None,
            "team2_moneyline": None,
            "event_id": "1011",
        }
    ]


def test_fetch_matchup_probabilities_extracts_moneylines_from_home_away_odds(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1014,
                competitors=[
                    _competitor("1", "Alpha", homeAway="home"),
                    _competitor("2", "Beta", homeAway="away"),
                ],
                probabilities=[
                    {"team": {"id": "1"}, "value": 61.0},
                    {"team": {"id": "2"}, "value": 39.0},
                ],
                odds=[
                    {
                        "homeTeamOdds": {"moneyLine": -135},
                        "awayTeamOdds": {"moneyLine": 115},
                    }
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_moneyline"] == -135
    assert rows[0]["team2_moneyline"] == 115


def test_fetch_matchup_probabilities_returns_none_moneylines_when_odds_missing(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1015,
                competitors=[
                    _competitor("1", "Alpha", probability=54.0),
                    _competitor("2", "Beta"),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_moneyline"] is None
    assert rows[0]["team2_moneyline"] is None


def test_fetch_matchup_probabilities_handles_partial_or_malformed_odds(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1016,
                competitors=[
                    _competitor("1", "Alpha", homeAway="home", probability=52.0),
                    _competitor("2", "Beta", homeAway="away"),
                ],
                odds=[
                    {
                        "homeTeamOdds": {"moneyLine": "bad"},
                        "awayTeamOdds": {},
                    }
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["team1_moneyline"] is None
    assert rows[0]["team2_moneyline"] is None



def test_fetch_matchup_probabilities_returns_multiple_events_in_source_order(monkeypatch, client):
    payload = {
        "events": [
            _event(
                1012,
                competitors=[
                    _competitor("1", "Alpha", probability=60),
                    _competitor("2", "Beta"),
                ],
            ),
            _event(
                1013,
                competitors=[
                    _competitor("3", "Gamma", probability=40),
                    _competitor("4", "Delta"),
                ],
            ),
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert [row["event_id"] for row in rows] == ["1012", "1013"]
    assert [row["team1"] for row in rows] == ["Alpha", "Gamma"]


def test_fetch_matchup_probabilities_preserves_event_id(monkeypatch, client):
    payload = {
        "events": [
            _event(
                9999,
                competitors=[
                    _competitor("1", "Alpha", probability=51.0),
                    _competitor("2", "Beta"),
                ],
            )
        ]
    }
    _mock_payload(monkeypatch, client, payload)

    rows = client.fetch_matchup_probabilities(2026)

    assert rows[0]["event_id"] == "9999"


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE_ESPN_TESTS") != "1", reason="Set RUN_LIVE_ESPN_TESTS=1 to run live ESPN smoke tests")
def test_fetch_matchup_probabilities_live_smoke():
    client = ESPNConnect(timeout=20)

    rows = client.fetch_matchup_probabilities(2026)

    assert isinstance(rows, list)
    for row in rows:
        assert set(["team1", "team2", "team1_probability", "team1_moneyline", "team2_moneyline", "event_id"]).issubset(row.keys())
        assert isinstance(row["team1"], str)
        assert isinstance(row["team2"], str)
        assert isinstance(row["team1_probability"], (int, float))
        assert 0.0 <= float(row["team1_probability"]) <= 100.0
