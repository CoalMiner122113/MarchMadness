"""
Frontend tests for the Streamlit March Madness client.

Uses Streamlit's built-in AppTest framework (available since 1.28+) to
exercise each page of the app without a live browser, and direct unit tests
for the pure helper functions defined in app.py.
"""

from pathlib import Path
import sys
import types
import pytest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = str(PROJECT_ROOT / "app.py")

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_EMPTY_FIX_RESULT = {
    "matched": 0,
    "skipped_existing": 0,
    "unmatched": 0,
    "ambiguous": 0,
    "unmatched_rows": [],
    "ambiguous_rows": [],
}
_EMPTY_SETUP_RESULT = {
    "year": 2026,
    "kenpom_rows": 0,
    "espn_rows": 0,
    "mapped_rows": 0,
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_services():
    """Patch all SQL and ESPN calls so tests run without live external services."""
    with (
        patch("sql.sqlHandler.getSeededBracket", return_value={}),
        patch("sql.sqlHandler.getTeamStatsForYear", return_value=[]),
        patch("sql.sqlHandler.getMBBTeams", return_value=[]),
        patch("sql.sqlHandler.fixTeamReferences", return_value=_EMPTY_FIX_RESULT),
        patch("sql.sqlHandler.updateTeamReferences", return_value=None),
        patch("sql.sqlHandler.setupmbbteams", return_value=_EMPTY_SETUP_RESULT),
        patch("sql.sqlHandler.replaceSeedsByYear", return_value=None),
        patch("sql.sqlHandler.upsertSeedsByYear", return_value=None),
        patch(
            "scraping.espnConnect.ESPNConnect.fetch_matchup_probabilities",
            return_value=[],
        ),
        patch(
            "scraping.espnConnect.ESPNConnect.fetch_raw_tournament_matchups",
            return_value=[],
        ),
        patch(
            "scraping.espnConnect.ESPNConnect.fetch_predictor_probabilities_for_session",
            return_value=[],
        ),
    ):
        yield


@pytest.fixture(scope="module")
def app_helpers():
    """
    Load pure helper functions from app.py without a live Streamlit context.

    A lightweight streamlit stub absorbs all module-level Streamlit calls
    (set_page_config, title, markdown, sidebar …) so the module loads cleanly
    and the pure Python helpers are accessible for direct unit testing.
    """

    class _StStub(types.ModuleType):
        """Minimal Streamlit stub that silently absorbs attribute access and calls."""

        def __getattr__(self, name):
            return _StStub(name)

        def __call__(self, *args, **kwargs):
            return _StStub("_result")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            return iter([])

        # set_page_config must be a no-op (first Streamlit call in app.py)
        def set_page_config(self, **kwargs):
            pass

        # cache_data is used as a decorator factory: @st.cache_data(show_spinner=False)
        def cache_data(self, fn=None, **kwargs):
            if fn is not None:
                return fn
            return lambda f: f

    st_stub = _StStub("streamlit")
    st_stub.session_state = {}

    with (
        patch.dict(sys.modules, {"streamlit": st_stub}),
        patch("sql.sqlHandler.getSeededBracket", return_value={}),
        patch("sql.sqlHandler.getTeamStatsForYear", return_value=[]),
        patch("sql.sqlHandler.getMBBTeams", return_value=[]),
        patch("sql.sqlHandler.fixTeamReferences", return_value=_EMPTY_FIX_RESULT),
        patch("sql.sqlHandler.updateTeamReferences", return_value=None),
        patch("sql.sqlHandler.setupmbbteams", return_value=_EMPTY_SETUP_RESULT),
        patch("sql.sqlHandler.replaceSeedsByYear", return_value=None),
        patch("sql.sqlHandler.upsertSeedsByYear", return_value=None),
        patch(
            "scraping.espnConnect.ESPNConnect.fetch_matchup_probabilities",
            return_value=[],
        ),
    ):
        import importlib.util

        spec = importlib.util.spec_from_file_location("_app_helpers", APP_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod


# ---------------------------------------------------------------------------
# AppTest smoke tests — each major page renders without an exception
# ---------------------------------------------------------------------------


class TestAppSmoke:
    """Verify that every navigation path renders without raising an exception."""

    def test_default_page_renders_without_exception(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        assert not at.exception

    def test_page_title_is_march_madness(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        titles = [t.value for t in at.title]
        assert any("March Madness" in t for t in titles)

    def test_view_seeding_page_is_default(self, mock_services):
        """The default subpage under March Madness is View Seeding."""
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        assert not at.exception
        subheaders = [s.value for s in at.subheader]
        assert any("Seeding" in s for s in subheaders)

    def test_run_simulation_page_renders(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        # sidebar.selectbox[1] is the subpage picker inside "March Madness"
        at.sidebar.selectbox[1].set_value("Run Simulation")
        at.run()
        assert not at.exception

    def test_view_brackets_page_renders(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.sidebar.selectbox[1].set_value("View Brackets")
        at.run()
        assert not at.exception

    def test_past_tournaments_page_renders(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.sidebar.selectbox[0].set_value("Past Tournaments")
        at.run()
        assert not at.exception

    def test_admin_update_team_references_renders(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.sidebar.selectbox[0].set_value("Admin")
        at.run()
        assert not at.exception

    def test_admin_debug_espn_page_renders(self, mock_services):
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        at.sidebar.selectbox[0].set_value("Admin")
        at.run()
        at.sidebar.selectbox[1].set_value("Debug ESPN Connection")
        at.run()
        assert not at.exception


# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------


class TestNameKey:
    def test_lowercases_and_strips_punctuation(self, app_helpers):
        assert app_helpers._name_key("Duke Blue Devils") == "dukebluedevils"

    def test_empty_string(self, app_helpers):
        assert app_helpers._name_key("") == ""

    def test_none_returns_empty_string(self, app_helpers):
        assert app_helpers._name_key(None) == ""

    def test_apostrophes_and_parens_stripped(self, app_helpers):
        assert app_helpers._name_key("St. Mary's (CA)") == "stmarysca"

    def test_digits_preserved(self, app_helpers):
        assert app_helpers._name_key("Team 1") == "team1"


class TestSortSeedRows:
    def test_orders_by_division_index_then_seed(self, app_helpers):
        rows = [
            {"division": "West", "seed": "1"},
            {"division": "South", "seed": "2"},
            {"division": "South", "seed": "1"},
            {"division": "East", "seed": "3"},
        ]
        result = app_helpers._sort_seed_rows(rows)
        assert result[0]["division"] == "South" and result[0]["seed"] == "1"
        assert result[1]["division"] == "South" and result[1]["seed"] == "2"
        assert result[2]["division"] == "East"
        assert result[3]["division"] == "West"

    def test_empty_list(self, app_helpers):
        assert app_helpers._sort_seed_rows([]) == []

    def test_all_same_division_sorted_by_seed(self, app_helpers):
        rows = [{"division": "East", "seed": str(s)} for s in [5, 1, 3]]
        result = app_helpers._sort_seed_rows(rows)
        seeds = [int(r["seed"]) for r in result]
        assert seeds == [1, 3, 5]


class TestCoerceProbabilityPercent:
    def test_valid_float(self, app_helpers):
        assert app_helpers._coerce_probability_percent(75.5) == 75.5

    def test_clamps_above_100(self, app_helpers):
        assert app_helpers._coerce_probability_percent(110.0) == 100.0

    def test_clamps_below_zero(self, app_helpers):
        assert app_helpers._coerce_probability_percent(-5.0) == 0.0

    def test_none_returns_none(self, app_helpers):
        assert app_helpers._coerce_probability_percent(None) is None

    def test_invalid_string_returns_none(self, app_helpers):
        assert app_helpers._coerce_probability_percent("bad") is None

    def test_string_number_coerced(self, app_helpers):
        assert app_helpers._coerce_probability_percent("60") == 60.0

    def test_rounds_to_two_decimal_places(self, app_helpers):
        result = app_helpers._coerce_probability_percent(33.3333)
        assert result == round(33.3333, 2)


class TestProbabilityOrDefault:
    def test_returns_value_when_valid(self, app_helpers):
        assert app_helpers._probability_or_default(80.0) == 80.0

    def test_returns_default_when_none(self, app_helpers):
        assert app_helpers._probability_or_default(None) == 50.0

    def test_custom_default(self, app_helpers):
        assert app_helpers._probability_or_default(None, default=65.0) == 65.0

    def test_clamps_via_coerce(self, app_helpers):
        assert app_helpers._probability_or_default(150.0) == 100.0


class TestMoneylineOrDefault:
    def test_valid_negative(self, app_helpers):
        assert app_helpers._moneyline_or_default(-150) == -150

    def test_none_returns_default(self, app_helpers):
        assert app_helpers._moneyline_or_default(None) == -100

    def test_float_rounds_to_int(self, app_helpers):
        assert app_helpers._moneyline_or_default(120.7) == 121

    def test_custom_default(self, app_helpers):
        assert app_helpers._moneyline_or_default(None, default=200) == 200


class TestKenpomStrength:
    def test_adj_em_only(self, app_helpers):
        entry = {"adj_em": 10.0, "sos": 0.0, "luck": 0.0}
        assert app_helpers._kenpom_strength(entry) == 10.0

    def test_sos_component_added(self, app_helpers):
        entry = {"adj_em": 0.0, "sos": 4.0, "luck": 0.0}
        # 0.35 * sqrt(4) = 0.7
        assert abs(app_helpers._kenpom_strength(entry) - 0.7) < 0.001

    def test_luck_multiplied_by_two(self, app_helpers):
        entry = {"adj_em": 0.0, "sos": 0.0, "luck": 1.5}
        assert abs(app_helpers._kenpom_strength(entry) - 3.0) < 0.001

    def test_negative_sos_uses_sign(self, app_helpers):
        entry = {"adj_em": 0.0, "sos": -9.0, "luck": 0.0}
        # 0.35 * -sqrt(9) = -1.05
        assert abs(app_helpers._kenpom_strength(entry) - (-1.05)) < 0.001


class TestLookupKenpomProbability:
    def test_stronger_team_wins_more_often(self, app_helpers):
        strong = {"adj_em": 30.0, "sos": 0.0, "luck": 0.0}
        weak = {"adj_em": 0.0, "sos": 0.0, "luck": 0.0}
        assert app_helpers._lookup_kenpom_probability(strong, weak) > 50.0

    def test_equal_teams_near_50_percent(self, app_helpers):
        avg = {"adj_em": 10.0, "sos": 1.0, "luck": 0.0}
        prob = app_helpers._lookup_kenpom_probability(avg, avg)
        assert abs(prob - 50.0) < 0.01

    def test_result_always_between_0_and_100(self, app_helpers):
        dominant = {"adj_em": 1000.0, "sos": 0.0, "luck": 0.0}
        terrible = {"adj_em": -1000.0, "sos": 0.0, "luck": 0.0}
        prob = app_helpers._lookup_kenpom_probability(dominant, terrible)
        assert 0.0 <= prob <= 100.0


class TestLookupEspnMatchup:
    _PROB_ROW = {
        "team1": "Duke",
        "team2": "Siena",
        "team1_probability": 90.0,
        "team2_probability": 10.0,
        "probability_available": True,
        "team1_moneyline": -800,
        "team2_moneyline": 500,
        "event_id": "42",
    }

    def test_found_forward_order(self, app_helpers):
        result = app_helpers._lookup_espn_matchup(
            [self._PROB_ROW],
            {"team_name": "Duke"},
            {"team_name": "Siena"},
        )
        assert result["available"] is True
        assert result["team1_probability"] == 90.0
        assert result["team2_probability"] == 10.0
        assert result["event_id"] == "42"

    def test_found_reversed_order_swaps_probabilities(self, app_helpers):
        result = app_helpers._lookup_espn_matchup(
            [self._PROB_ROW],
            {"team_name": "Siena"},
            {"team_name": "Duke"},
        )
        assert result["team1_probability"] == 10.0
        assert result["team2_probability"] == 90.0

    def test_not_found_defaults_to_50_50(self, app_helpers):
        result = app_helpers._lookup_espn_matchup(
            [],
            {"team_name": "TeamA"},
            {"team_name": "TeamB"},
        )
        assert result["available"] is False
        assert result["team1_probability"] == 50.0
        assert result["team2_probability"] == 50.0

    def test_unavailable_row_fills_complement(self, app_helpers):
        row = {
            "team1": "Alpha",
            "team2": "Beta",
            "team1_probability": None,
            "team2_probability": 30.0,
            "probability_available": False,
            "team1_moneyline": None,
            "team2_moneyline": None,
            "event_id": None,
        }
        result = app_helpers._lookup_espn_matchup(
            [row],
            {"team_name": "Alpha"},
            {"team_name": "Beta"},
        )
        assert result["available"] is False
        assert abs(result["team1_probability"] - 70.0) < 0.01
        assert abs(result["team2_probability"] - 30.0) < 0.01



class TestBuildProbabilityRows:
    def test_missing_espn_probability_falls_back_to_kenpom(self, app_helpers):
        payload = {"year": 2026, "simulation": {"round_inputs": {}}}
        pending_games = [{
            "division": "South",
            "team1": {"team_name": "Alpha", "seed": 1, "adj_em": 30.0, "sos": 10.0, "luck": 0.0},
            "team2": {"team_name": "Beta", "seed": 16, "adj_em": 5.0, "sos": -2.0, "luck": 0.0},
        }]

        rows = app_helpers._build_probability_rows(
            payload,
            "Round of 64",
            pending_games,
            "ESPN Probability",
            prob_rows=[],
            raw_rows=[],
        )

        assert len(rows) == 2
        assert rows[0]["espn_available"] is False
        assert rows[0]["espn_probability"] == rows[0]["kenpom_probability"]
        assert rows[1]["espn_probability"] == rows[1]["kenpom_probability"]
        assert rows[0]["moneyline"] == -100
        assert rows[1]["moneyline"] == -100
        assert rows[0]["simulation_probability"] == rows[0]["kenpom_probability"]
        assert rows[1]["simulation_probability"] == rows[1]["kenpom_probability"]
