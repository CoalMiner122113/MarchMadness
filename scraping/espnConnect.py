import html
import json
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from dotenv import dotenv_values

from sql.sqlHandler import upsertSeedsByYear, upsertTeamNameMappings


config = dotenv_values(".env")


class ESPNConnect:
    """Simple ESPN API connector for team metadata, seeds, matchup probabilities, and predictor flows."""

    PREDICTOR_PAGE_URL_TEMPLATE = "https://fantasy.espn.com/games/tournament-challenge-bracket-{year}/predictor"
    PREDICTOR_ROUND_IDS = {
        "Round of 64": ["rnd1_east", "rnd1_south", "rnd1_west", "rnd1_midwest"],
        "Round of 32": ["rnd2_east_south", "rnd2_west_midwest"],
        "Sweet 16": ["rnd3_16"],
        "Elite 8": ["rnd4_8"],
        "Final Four": ["rnd5_4"],
        "Championship": ["rnd6_champ"],
    }
    ROUND_SEQUENCE = [
        "Round of 64",
        "Round of 32",
        "Sweet 16",
        "Elite 8",
        "Final Four",
        "Championship",
    ]

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.base_url = config.get(
            "ESPN_BASE_URL",
            "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        )
        self.default_headers = {
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "User-Agent": "MarchMadnessBot/1.0",
        }

    def _get_text_url(self, url: str) -> str:
        request = Request(url, headers=self.default_headers)
        with urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    def _post_form_text(self, url: str, data: Dict[str, object]) -> str:
        encoded = urlencode({k: "" if v is None else v for k, v in data.items()}).encode("utf-8")
        headers = dict(self.default_headers)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=encoded, headers=headers, method="POST")
        with urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    def _get_json(self, path: str, params: Optional[Dict] = None) -> dict:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"

        request = Request(url, headers=self.default_headers)
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_form_json(self, url: str, data: Dict[str, object]) -> dict:
        response_text = self._post_form_text(url, data)
        return json.loads(response_text)

    def test_api_connection(self) -> Dict[str, object]:
        payload = self._get_json("teams", params={"limit": 5})
        teams = self._extract_team_list(payload)
        return {
            "ok": True,
            "sample_team_count": len(teams),
            "sample_teams": teams[:3],
        }

    def fetch_team_info(self, limit: int = 400) -> List[dict]:
        payload = self._get_json("teams", params={"limit": int(limit)})
        return self._extract_team_list(payload)

    def fetch_team_catalog(self, limit: int = 400) -> List[dict]:
        return self.fetch_team_info(limit=limit)

    def _extract_team_list(self, payload: dict) -> List[dict]:
        extracted: List[dict] = []
        sports = payload.get("sports", [])
        if not sports:
            return extracted

        leagues = sports[0].get("leagues", [])
        if not leagues:
            return extracted

        for row in leagues[0].get("teams", []):
            raw_team = row.get("team", row)
            display = (raw_team.get("displayName") or "").strip()
            short_display = (raw_team.get("shortDisplayName") or display).strip()
            extracted.append(
                {
                    "espn_id": raw_team.get("id"),
                    "espn_uid": raw_team.get("uid"),
                    "espn_name": display,
                    "abbreviation": (raw_team.get("abbreviation") or "").strip(),
                    "short_name": short_display,
                    "display_name": display,
                }
            )

        return extracted

    def _coerce_moneyline(self, value) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, dict):
            for key in ("moneyLine", "moneyline", "american", "value", "current"):
                coerced = self._coerce_moneyline(value.get(key))
                if coerced is not None:
                    return coerced
            return None
        if isinstance(value, (int, float)):
            return int(round(float(value)))

        text = str(value).strip()
        if not text:
            return None
        match = re.search(r"[+-]?\d+", text)
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def _extract_moneylines(self, competition: dict, c1: dict, c2: dict) -> Tuple[Optional[int], Optional[int]]:
        odds_rows = competition.get("odds") or []
        if isinstance(odds_rows, dict):
            odds_rows = [odds_rows]

        team1_id = str(c1.get("team", {}).get("id") or "").strip()
        team2_id = str(c2.get("team", {}).get("id") or "").strip()
        home_away_to_index = {
            str(c1.get("homeAway") or "").lower(): 0,
            str(c2.get("homeAway") or "").lower(): 1,
        }

        for odds in odds_rows:
            team_moneylines: List[Optional[int]] = [None, None]

            for side_key, side_name in (("homeTeamOdds", "home"), ("awayTeamOdds", "away")):
                side_data = odds.get(side_key)
                if side_data is None:
                    continue
                side_index = home_away_to_index.get(side_name)
                moneyline = self._coerce_moneyline(side_data)
                if side_index is not None and moneyline is not None:
                    team_moneylines[side_index] = moneyline

            for side_key, side_name in (("homeMoneyLine", "home"), ("awayMoneyLine", "away")):
                side_index = home_away_to_index.get(side_name)
                moneyline = self._coerce_moneyline(odds.get(side_key))
                if side_index is not None and moneyline is not None:
                    team_moneylines[side_index] = moneyline

            participants = odds.get("participants") or odds.get("teams") or odds.get("competitors") or []
            for participant in participants:
                participant_id = str(
                    participant.get("teamId")
                    or participant.get("id")
                    or participant.get("competitorId")
                    or ""
                ).strip()
                moneyline = self._coerce_moneyline(participant)
                if participant_id == team1_id and moneyline is not None:
                    team_moneylines[0] = moneyline
                elif participant_id == team2_id and moneyline is not None:
                    team_moneylines[1] = moneyline

            if any(value is not None for value in team_moneylines):
                return team_moneylines[0], team_moneylines[1]

        return None, None

    def _match_key(self, value: str) -> str:
        return "".join(ch for ch in (value or "").lower() if ch.isalnum())

    def _entry_match_keys(self, entry) -> Set[str]:
        if entry is None:
            return set()
        if isinstance(entry, str):
            values = [entry]
        elif isinstance(entry, dict):
            values = [
                entry.get("team_name"),
                entry.get("espn_name"),
                entry.get("ncaa_name"),
                entry.get("KenPomName"),
                entry.get("EspnName"),
                entry.get("NcaaName"),
                entry.get("winner"),
                entry.get("team1"),
                entry.get("team2"),
            ]
        else:
            values = [str(entry)]

        return {self._match_key(value) for value in values if value}

    def _extract_predictor_url(self, html_text: str) -> str:
        match = re.search(r'bracketPredictorURL":"([^"]+)"', html_text)
        if not match:
            raise RuntimeError("Unable to locate bracketPredictorURL in predictor page HTML.")
        return html.unescape(match.group(1)).replace('\/', '/')

    def _extract_js_var(self, html_text: str, var_name: str) -> str:
        patterns = [
            rf"var\s+{re.escape(var_name)}\s*=\s*'([^']*)'",
            rf'var\s+{re.escape(var_name)}\s*=\s*"([^"]*)"',
            rf"var\s+{re.escape(var_name)}\s*=\s*([^;]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, html_text)
            if match:
                return match.group(1).strip()
        raise RuntimeError(f"Unable to locate predictor var: {var_name}")

    def _parse_boolish(self, value: str) -> str:
        return str(value).strip().lower()

    def fetch_predictor_bootstrap(self, year: int) -> Dict[str, object]:
        predictor_page_url = self.PREDICTOR_PAGE_URL_TEMPLATE.format(year=int(year))
        predictor_page_html = self._get_text_url(predictor_page_url)
        predictor_url = self._extract_predictor_url(predictor_page_html)
        predictor_html = self._get_text_url(predictor_url)

        predictor_parts = urlsplit(predictor_url)
        predictor_origin = f"{predictor_parts.scheme}://{predictor_parts.netloc}"
        espn_file_version = self._extract_js_var(predictor_html, "espn_file_version")

        return {
            "year": int(year),
            "predictor_page_url": predictor_page_url,
            "predictor_url": predictor_url,
            "predictor_origin": predictor_origin,
            "ajax_base_url": f"{predictor_origin}/ajax/espn/bracket-predictor/{espn_file_version}",
            "league_abbr": self._extract_js_var(predictor_html, "league_abbr"),
            "bracket_id": int(self._extract_js_var(predictor_html, "bracket_id")),
            "espn_file_version": str(espn_file_version),
            "is_iframe": self._parse_boolish(self._extract_js_var(predictor_html, "is_iframe")),
            "theme": self._extract_js_var(predictor_html, "theme"),
            "theme_explicit": self._parse_boolish(self._extract_js_var(predictor_html, "theme_explicit")),
            "team_logo_version": self._extract_js_var(predictor_html, "team_logo_version"),
        }

    def _predictor_ajax_url(self, predictor_state: Dict[str, object], endpoint: str) -> str:
        return f"{str(predictor_state['ajax_base_url']).rstrip('/')}/{endpoint.lstrip('/')}"

    def _parse_pct_text(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        match = re.search(r"\d+(?:\.\d+)?", value)
        if not match:
            return None
        return round(float(match.group(0)), 2)

    def _parse_predictor_matchup_details(self, matchup_details_html: str, round_id: str) -> List[dict]:
        soup = BeautifulSoup(matchup_details_html or "", "html.parser")
        rows: List[dict] = []

        for matchup in soup.select("div.matchup"):
            picks = matchup.select(".teams .team a.pick")
            if len(picks) < 2:
                continue

            pick1, pick2 = picks[0], picks[1]
            team1_name = (pick1.get("data-team-name") or pick1.select_one(".team-name") or "")
            team2_name = (pick2.get("data-team-name") or pick2.select_one(".team-name") or "")
            if hasattr(team1_name, "get_text"):
                team1_name = team1_name.get_text(" ", strip=True)
            if hasattr(team2_name, "get_text"):
                team2_name = team2_name.get_text(" ", strip=True)
            team1_name = str(team1_name).strip()
            team2_name = str(team2_name).strip()
            if not team1_name or not team2_name:
                continue

            overall_team1 = matchup.select_one(".overall-team1 .pct")
            overall_team2 = matchup.select_one(".overall-team2 .pct")
            team1_probability = self._parse_pct_text(overall_team1.get_text(" ", strip=True) if overall_team1 else None)
            team2_probability = self._parse_pct_text(overall_team2.get_text(" ", strip=True) if overall_team2 else None)
            team1_seed_el = pick1.select_one(".seed span")
            team2_seed_el = pick2.select_one(".seed span")
            team1_region_el = pick1.select_one(".original-region")
            team2_region_el = pick2.select_one(".original-region")

            rows.append(
                {
                    "round_id": round_id,
                    "round_num": int(matchup.get("data-round-num") or 0),
                    "game_number": int(matchup.get("data-game-num") or 0),
                    "team1": team1_name,
                    "team2": team2_name,
                    "team1_predictor_id": pick1.get("data-team-id"),
                    "team2_predictor_id": pick2.get("data-team-id"),
                    "team1_seed": int(team1_seed_el.get_text(strip=True)) if team1_seed_el and team1_seed_el.get_text(strip=True).isdigit() else None,
                    "team2_seed": int(team2_seed_el.get_text(strip=True)) if team2_seed_el and team2_seed_el.get_text(strip=True).isdigit() else None,
                    "team1_region": team1_region_el.get_text(strip=True) if team1_region_el else None,
                    "team2_region": team2_region_el.get_text(strip=True) if team2_region_el else None,
                    "team1_probability": team1_probability,
                    "team2_probability": team2_probability,
                    "probability_available": team1_probability is not None and team2_probability is not None,
                    "team1_moneyline": None,
                    "team2_moneyline": None,
                    "event_id": None,
                }
            )

        return rows

    def fetch_predictor_round(self, year: int, predictor_state: Dict[str, object], round_id: str, game_number: Optional[int] = None) -> List[dict]:
        del year
        data = {
            "l": predictor_state["league_abbr"],
            "b": predictor_state["bracket_id"],
            "r": round_id,
            "espn_file_version": predictor_state["espn_file_version"],
            "is_iframe": predictor_state["is_iframe"],
            "theme": predictor_state["theme"],
            "theme_explicit": predictor_state["theme_explicit"],
            "team_logo_version": predictor_state["team_logo_version"],
        }
        if game_number is not None:
            data["g"] = int(game_number)

        payload = self._post_form_json(self._predictor_ajax_url(predictor_state, "getMatchups.php"), data)
        return self._parse_predictor_matchup_details(payload.get("matchup_details", ""), round_id)

    def apply_predictor_pick(self, year: int, predictor_state: Dict[str, object], round_number: int, game_number: int, team_id: str) -> Dict[str, object]:
        del year
        data = {
            "l": predictor_state["league_abbr"],
            "b": predictor_state["bracket_id"],
            "type": "single",
            "r": int(round_number),
            "g": int(game_number),
            "p": str(team_id),
        }
        return self._post_form_json(self._predictor_ajax_url(predictor_state, "makePick.php"), data)

    def _fetch_predictor_app_round(self, year: int, predictor_state: Dict[str, object], round_name: str) -> List[dict]:
        rows: List[dict] = []
        for round_id in self.PREDICTOR_ROUND_IDS.get(round_name, []):
            rows.extend(self.fetch_predictor_round(year, predictor_state, round_id))
        return rows

    def _find_predictor_match_for_winner(self, matchups: List[dict], winner_entry, used_keys: Set[Tuple[int, int]]) -> Tuple[Optional[dict], Optional[str]]:
        winner_keys = self._entry_match_keys(winner_entry)
        if not winner_keys:
            return None, None

        for matchup in matchups:
            match_key = (int(matchup.get("round_num") or 0), int(matchup.get("game_number") or 0))
            if match_key in used_keys:
                continue

            team1_keys = self._entry_match_keys(matchup.get("team1"))
            team2_keys = self._entry_match_keys(matchup.get("team2"))
            if winner_keys & team1_keys:
                return matchup, str(matchup.get("team1_predictor_id") or "")
            if winner_keys & team2_keys:
                return matchup, str(matchup.get("team2_predictor_id") or "")

        return None, None

    def fetch_predictor_probabilities_for_session(self, year: int, session_bracket_state: Dict[str, object]) -> List[dict]:
        target_round = session_bracket_state.get("target_round")
        if target_round not in self.PREDICTOR_ROUND_IDS:
            return []

        predictor_state = self.fetch_predictor_bootstrap(year)
        winners_by_round = session_bracket_state.get("winners", {}) or {}
        target_index = self.ROUND_SEQUENCE.index(target_round)

        for round_name in self.ROUND_SEQUENCE[:target_index]:
            round_matchups = self._fetch_predictor_app_round(year, predictor_state, round_name)
            used_keys: Set[Tuple[int, int]] = set()

            for winner_row in winners_by_round.get(round_name, []):
                winner_entry = winner_row.get("team") if isinstance(winner_row, dict) else winner_row
                matchup, predictor_team_id = self._find_predictor_match_for_winner(round_matchups, winner_entry, used_keys)
                if not matchup or not predictor_team_id:
                    continue

                result = self.apply_predictor_pick(
                    year,
                    predictor_state,
                    int(matchup.get("round_num") or 0),
                    int(matchup.get("game_number") or 0),
                    predictor_team_id,
                )
                if str(result.get("status")) == "1":
                    used_keys.add((int(matchup.get("round_num") or 0), int(matchup.get("game_number") or 0)))

        return self._fetch_predictor_app_round(year, predictor_state, target_round)

    def fetch_raw_tournament_matchups(self, year: int) -> List[dict]:
        payload = self._get_json(
            "scoreboard",
            params={
                "limit": 1000,
                "groups": 50,
                "seasontype": 3,
                "dates": f"{int(year)}0318-{int(year)}0409",
            },
        )

        rows: List[dict] = []
        for event in payload.get("events", []):
            event_id = event.get("id")
            event_name = event.get("name")
            for competition in event.get("competitions", []):
                competitors = competition.get("competitors", [])
                if len(competitors) < 2:
                    continue

                c1 = competitors[0]
                c2 = competitors[1]
                t1 = c1.get("team", {})
                t2 = c2.get("team", {})
                team1_name = (t1.get("displayName") or "").strip()
                team2_name = (t2.get("displayName") or "").strip()
                if not team1_name or not team2_name:
                    continue

                team1_moneyline, team2_moneyline = self._extract_moneylines(competition, c1, c2)

                p1 = None
                probs = competition.get("probabilities") or []
                if probs:
                    by_id: Dict[str, float] = {}
                    for p in probs:
                        team_ref = p.get("team") or {}
                        team_id = str(team_ref.get("id") or p.get("teamId") or "").strip()
                        try:
                            value = float(p.get("value"))
                        except (TypeError, ValueError):
                            value = None
                        if team_id and value is not None:
                            by_id[team_id] = value

                    team1_id = str(t1.get("id") or "").strip()
                    if team1_id in by_id:
                        p1 = by_id[team1_id]

                if p1 is None:
                    for candidate in (c1.get("probability"), c1.get("winProbability"), c1.get("chanceToWin")):
                        try:
                            p1 = float(candidate)
                            if p1 <= 1.0:
                                p1 *= 100.0
                            break
                        except (TypeError, ValueError):
                            continue

                rows.append(
                    {
                        "event_id": event_id,
                        "event_name": event_name,
                        "competition_id": competition.get("id"),
                        "team1": team1_name,
                        "team2": team2_name,
                        "team1_espn_id": t1.get("id"),
                        "team2_espn_id": t2.get("id"),
                        "team1_seed": c1.get("seed") or c1.get("curatedRank", {}).get("current"),
                        "team2_seed": c2.get("seed") or c2.get("curatedRank", {}).get("current"),
                        "team1_region": c1.get("tournamentSeed") or c1.get("region"),
                        "team2_region": c2.get("tournamentSeed") or c2.get("region"),
                        "team1_home_away": c1.get("homeAway"),
                        "team2_home_away": c2.get("homeAway"),
                        "probability_available": p1 is not None,
                        "team1_probability": round(max(0.0, min(100.0, p1)), 2) if p1 is not None else None,
                        "team2_probability": round(max(0.0, min(100.0, 100.0 - p1)), 2) if p1 is not None else None,
                        "team1_moneyline": team1_moneyline,
                        "team2_moneyline": team2_moneyline,
                    }
                )

        return rows

    def debug_raw_matchup(self, year: int, team1: str, team2: str) -> Dict[str, object]:
        rows = self.fetch_raw_tournament_matchups(year)
        requested_key = f"{self._match_key(team1)}|{self._match_key(team2)}"
        reverse_key = f"{self._match_key(team2)}|{self._match_key(team1)}"

        exact_matches = []
        candidate_rows = []
        for row in rows:
            row_key = f"{self._match_key(row.get('team1', ''))}|{self._match_key(row.get('team2', ''))}"
            if row_key in (requested_key, reverse_key):
                exact_matches.append(row)
                continue

            row_names = f"{row.get('team1', '')} {row.get('team2', '')}".lower()
            if team1.lower() in row_names or team2.lower() in row_names:
                candidate_rows.append(row)

        return {
            "year": int(year),
            "requested_matchup": {
                "team1": team1,
                "team2": team2,
                "requested_key": requested_key,
                "reverse_key": reverse_key,
            },
            "fetched_row_count": len(rows),
            "exact_match_count": len(exact_matches),
            "candidate_match_count": len(candidate_rows),
            "exact_matches": exact_matches,
            "candidate_rows": candidate_rows[:20],
            "sample_rows": rows[:20],
        }

    def fetch_matchup_probabilities(self, year: int) -> List[dict]:
        """
        Pull matchup predictor probabilities from ESPN scoreboard where available.

        Returns rows with team1/team2, team1_probability in percent [0, 100],
        and optional team-level moneylines when present in the payload.
        """
        payload = self._get_json(
            "scoreboard",
            params={
                "limit": 1000,
                "groups": 50,
                "seasontype": 3,
                "dates": f"{int(year)}0318-{int(year)}0409",
            },
        )

        rows: List[dict] = []
        for event in payload.get("events", []):
            for competition in event.get("competitions", []):
                competitors = competition.get("competitors", [])
                if len(competitors) < 2:
                    continue

                c1 = competitors[0]
                c2 = competitors[1]
                t1 = c1.get("team", {})
                t2 = c2.get("team", {})

                team1_name = (t1.get("displayName") or "").strip()
                team2_name = (t2.get("displayName") or "").strip()
                if not team1_name or not team2_name:
                    continue

                p1 = None
                probs = competition.get("probabilities") or []
                if probs:
                    by_id: Dict[str, float] = {}
                    for p in probs:
                        team_ref = p.get("team") or {}
                        team_id = str(team_ref.get("id") or p.get("teamId") or "").strip()
                        try:
                            value = float(p.get("value"))
                        except (TypeError, ValueError):
                            value = None
                        if team_id and value is not None:
                            by_id[team_id] = value

                    team1_id = str(t1.get("id") or "").strip()
                    if team1_id in by_id:
                        p1 = by_id[team1_id]

                if p1 is None:
                    for candidate in (c1.get("probability"), c1.get("winProbability"), c1.get("chanceToWin")):
                        try:
                            p1 = float(candidate)
                            if p1 <= 1.0:
                                p1 *= 100.0
                            break
                        except (TypeError, ValueError):
                            continue

                if p1 is None:
                    continue

                team1_moneyline, team2_moneyline = self._extract_moneylines(competition, c1, c2)
                p1 = max(0.0, min(100.0, p1))
                rows.append(
                    {
                        "team1": team1_name,
                        "team2": team2_name,
                        "team1_probability": round(p1, 2),
                        "team1_moneyline": team1_moneyline,
                        "team2_moneyline": team2_moneyline,
                        "event_id": event.get("id"),
                    }
                )

        return rows

    def build_name_mappings(self, espn_teams: Iterable[dict], manual_overrides: Optional[Dict[str, str]] = None) -> List[dict]:
        manual_overrides = manual_overrides or {}
        mappings: List[dict] = []
        for kenpom_name, espn_name in manual_overrides.items():
            mappings.append(
                {
                    "kenpom_name": kenpom_name,
                    "espn_name": espn_name,
                    "ncaa_name": kenpom_name,
                }
            )
        return mappings

    def upsert_team_mappings(self, mappings: Iterable[dict]):
        upsertTeamNameMappings(mappings)

    def fetch_tournament_seed_data(self, year: int) -> List[dict]:
        payload = self._get_json(
            "scoreboard",
            params={
                "limit": 1000,
                "groups": 50,
                "seasontype": 3,
                "dates": f"{int(year)}0318-{int(year)}0409",
            },
        )

        division_name_to_id = {
            "south": 1,
            "east": 2,
            "west": 3,
            "midwest": 4,
        }

        unique: Dict[str, dict] = {}
        for event in payload.get("events", []):
            for competition in event.get("competitions", []):
                for comp in competition.get("competitors", []):
                    team_data = comp.get("team", {})
                    espn_name = (team_data.get("displayName") or "").strip()
                    if not espn_name:
                        continue

                    seed_value = comp.get("seed") or comp.get("curatedRank", {}).get("current")
                    if seed_value is None:
                        continue

                    region_text = (comp.get("tournamentSeed") or comp.get("region") or "")
                    region_text = str(region_text).lower()

                    division_id = None
                    for name, div_id in division_name_to_id.items():
                        if name in region_text:
                            division_id = div_id
                            break

                    if division_id is None:
                        continue

                    unique[espn_name] = {
                        "espn_name": espn_name,
                        "espn_id": team_data.get("id"),
                        "espn_uid": team_data.get("uid"),
                        "seed": int(seed_value),
                        "division_id": division_id,
                    }

        return list(unique.values())

    def upsert_seed_data(self, seed_rows: Iterable[dict], year: int):
        upsertSeedsByYear(seed_rows, year)

    def test_seed_pull(self, year: int) -> Dict[str, object]:
        rows = self.fetch_tournament_seed_data(year)
        return {
            "ok": True,
            "year": int(year),
            "row_count": len(rows),
            "sample": rows[:10],
        }


if __name__ == "__main__":
    client = ESPNConnect()
    print("API test:", client.test_api_connection())


