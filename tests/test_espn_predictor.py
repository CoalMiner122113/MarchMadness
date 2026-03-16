from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scraping.espnConnect import ESPNConnect


PREDICTOR_PAGE_HTML = """
<html><body><script>
window.__STATE__ = {"clientFlags":{"bracketPredictorURL":"https://feeds.teamrankings.com/espn/ncaa-tournament-men/bracket-predictor/?iframe=true&platform=web&theme=light"}};
</script></body></html>
"""

PREDICTOR_IFRAME_HTML = """
<html><body><script>
var league_abbr = 'ncb';
var bracket_id = 35601;
var espn_file_version = 26;
var is_iframe = true;
var theme = 'light';
var theme_explicit = true;
var team_logo_version = '2025-ncb';
</script></body></html>
"""

MATCHUP_HTML = """
<div class="matchup no-pick clearfix" id="r1g0" data-round-num="1" data-game-num="0">
  <div class="teams">
    <div class="team team1">
      <a class="pick pick1" data-team-id="391" data-team-name="Duke">
        <div class="seed-and-region-wrapper">
          <p class="seed">#<span>1</span> Seed</p>
          <p class="original-region">East</p>
        </div>
      </a>
    </div>
    <div class="team team2">
      <a class="pick pick2" data-team-id="380" data-team-name="Siena">
        <div class="seed-and-region-wrapper">
          <p class="seed">#<span>16</span> Seed</p>
          <p class="original-region">East</p>
        </div>
      </a>
    </div>
  </div>
  <div class="overall-prediction-wrapper">
    <div class="overall-team overall-team1"><div class="pct favored">99%</div></div>
    <div class="overall-team overall-team2"><div class="pct">1%</div></div>
  </div>
</div>
"""


@pytest.fixture
def client():
    return ESPNConnect()


def test_fetch_predictor_bootstrap_extracts_predictor_state(monkeypatch, client):
    responses = {
        client.PREDICTOR_PAGE_URL_TEMPLATE.format(year=2026): PREDICTOR_PAGE_HTML,
        "https://feeds.teamrankings.com/espn/ncaa-tournament-men/bracket-predictor/?iframe=true&platform=web&theme=light": PREDICTOR_IFRAME_HTML,
    }
    monkeypatch.setattr(client, "_get_text_url", lambda url: responses[url])

    state = client.fetch_predictor_bootstrap(2026)

    assert state["league_abbr"] == "ncb"
    assert state["bracket_id"] == 35601
    assert state["espn_file_version"] == "26"
    assert state["ajax_base_url"] == "https://feeds.teamrankings.com/ajax/espn/bracket-predictor/26"


def test_fetch_predictor_round_parses_matchup_details(monkeypatch, client):
    predictor_state = {
        "league_abbr": "ncb",
        "bracket_id": 35601,
        "espn_file_version": "26",
        "is_iframe": "true",
        "theme": "light",
        "theme_explicit": "true",
        "team_logo_version": "2025-ncb",
        "ajax_base_url": "https://feeds.teamrankings.com/ajax/espn/bracket-predictor/26",
    }
    monkeypatch.setattr(client, "_post_form_json", lambda url, data: {"matchup_details": MATCHUP_HTML})

    rows = client.fetch_predictor_round(2026, predictor_state, "rnd1_east")

    assert rows == [
        {
            "round_id": "rnd1_east",
            "round_num": 1,
            "game_number": 0,
            "team1": "Duke",
            "team2": "Siena",
            "team1_predictor_id": "391",
            "team2_predictor_id": "380",
            "team1_seed": 1,
            "team2_seed": 16,
            "team1_region": "East",
            "team2_region": "East",
            "team1_probability": 99.0,
            "team2_probability": 1.0,
            "probability_available": True,
            "team1_moneyline": None,
            "team2_moneyline": None,
            "event_id": None,
        }
    ]


def test_apply_predictor_pick_posts_expected_payload(monkeypatch, client):
    predictor_state = {
        "league_abbr": "ncb",
        "bracket_id": 35601,
        "espn_file_version": "26",
        "ajax_base_url": "https://feeds.teamrankings.com/ajax/espn/bracket-predictor/26",
    }
    seen = {}

    def fake_post(url, data):
        seen["url"] = url
        seen["data"] = data
        return {"status": 1}

    monkeypatch.setattr(client, "_post_form_json", fake_post)

    result = client.apply_predictor_pick(2026, predictor_state, 1, 0, "391")

    assert result == {"status": 1}
    assert seen["url"].endswith("/makePick.php")
    assert seen["data"] == {
        "l": "ncb",
        "b": 35601,
        "type": "single",
        "r": 1,
        "g": 0,
        "p": "391",
    }


def test_fetch_predictor_probabilities_for_session_replays_winners(monkeypatch, client):
    monkeypatch.setattr(client, "fetch_predictor_bootstrap", lambda year: {"bootstrap": True})
    applied = []

    round1_rows = [
        {
            "round_id": "rnd1_east",
            "round_num": 1,
            "game_number": 0,
            "team1": "Connecticut",
            "team2": "Furman",
            "team1_predictor_id": "635",
            "team2_predictor_id": "524",
            "team1_probability": 98.0,
            "team2_probability": 2.0,
        }
    ]
    round2_rows = [
        {
            "round_id": "rnd2_east_south",
            "round_num": 2,
            "game_number": 0,
            "team1": "Connecticut",
            "team2": "Duke",
            "team1_predictor_id": "635",
            "team2_predictor_id": "391",
            "team1_probability": 53.0,
            "team2_probability": 47.0,
        }
    ]

    def fake_fetch_app_round(year, predictor_state, round_name):
        if round_name == "Round of 64":
            return round1_rows
        if round_name == "Round of 32":
            return round2_rows
        return []

    def fake_apply(year, predictor_state, round_number, game_number, team_id):
        applied.append((round_number, game_number, team_id))
        return {"status": 1}

    monkeypatch.setattr(client, "_fetch_predictor_app_round", fake_fetch_app_round)
    monkeypatch.setattr(client, "apply_predictor_pick", fake_apply)

    rows = client.fetch_predictor_probabilities_for_session(
        2026,
        {
            "target_round": "Round of 32",
            "winners": {
                "Round of 64": [
                    {"team": {"team_name": "UConn", "espn_name": "Connecticut"}},
                ]
            },
        },
    )

    assert applied == [(1, 0, "635")]
    assert rows == round2_rows
