import json
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import dotenv_values

from sql.sqlHandler import upsertSeedsByYear, upsertTeamNameMappings


config = dotenv_values(".env")


class ESPNConnect:
    """Simple ESPN API connector for team metadata and tournament seed pulls."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.base_url = config.get(
            "ESPN_BASE_URL",
            "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball",
        )
        self.default_headers = {
            "Accept": "application/json",
            "User-Agent": "MarchMadnessBot/1.0",
        }

    def _get_json(self, path: str, params: Optional[Dict] = None) -> dict:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"

        request = Request(url, headers=self.default_headers)
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

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

    def build_name_mappings(self, espn_teams: Iterable[dict], manual_overrides: Optional[Dict[str, str]] = None) -> List[dict]:
        manual_overrides = manual_overrides or {}
        rows: List[dict] = []

        for kenpom_name, espn_name in manual_overrides.items():
            rows.append(
                {
                    "kenpom_name": kenpom_name,
                    "espn_name": espn_name,
                    "ncaa_name": kenpom_name,
                }
            )

        return rows

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
        events = payload.get("events", [])
        for event in events:
            competitions = event.get("competitions", [])
            for competition in competitions:
                for comp in competition.get("competitors", []):
                    team_data = comp.get("team", {})
                    espn_name = (team_data.get("displayName") or "").strip()
                    if not espn_name:
                        continue

                    seed_value = comp.get("seed") or comp.get("curatedRank", {}).get("current")
                    if seed_value is None:
                        continue

                    region_text = (comp.get("tournamentSeed") or "")
                    if not region_text:
                        region_text = (comp.get("region") or "")

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
    connection_result = client.test_api_connection()
    print("API test:", connection_result)
