from typing import Dict, Iterable, List, Optional

import mysql.connector as sql
from mysql.connector import Error
from dotenv import dotenv_values

from app_logic.objDef import team


config = dotenv_values(".env")
DB_NAME = config.get("MYSQL_DB", "marchMadness")

DIVISION_NAME_TO_ID = {
    "south": 1,
    "east": 2,
    "west": 3,
    "midwest": 4,
}


def _connection_config(include_database: bool = True) -> Dict[str, str]:
    cfg = {
        "host": config.get("MYSQL_HOST"),
        "user": config.get("MYSQL_USER"),
        "password": config.get("MYSQL_PASS"),
    }
    if include_database:
        cfg["database"] = DB_NAME
    return cfg


def getConnection(include_database: bool = True):
    """Compatibility wrapper used by legacy code."""
    try:
        return sql.connect(**_connection_config(include_database=include_database))
    except Error as e:
        raise RuntimeError(f"DB connection failed: {e}") from e


def setup():
    """Compatibility wrapper used by legacy code."""
    return getConnection(include_database=True)


def ensure_teamstats_fk_targets_mbbteams():
    """Repair TeamStatsByYear.TeamID FK if it still references oldmbbteams."""
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'TeamStatsByYear'
              AND COLUMN_NAME = 'TeamID'
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """
        )
        row = cursor.fetchone()
        if row and str(row[1]).lower() != 'mbbteams':
            constraint_name = row[0]
            cursor.execute(f"ALTER TABLE TeamStatsByYear DROP FOREIGN KEY {constraint_name}")
            cursor.execute(
                """
                ALTER TABLE TeamStatsByYear
                ADD CONSTRAINT fk_teamstats_teamid
                FOREIGN KEY (TeamID)
                REFERENCES MBBTeams(TeamID)
                ON DELETE CASCADE
                ON UPDATE CASCADE
                """
            )
            conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"ensure_teamstats_fk_targets_mbbteams failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def _normalize_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _upsert_team(
    cursor,
    kenpom_name: str,
    espn_name: Optional[str] = None,
    ncaa_name: Optional[str] = None,
    espn_id: Optional[str] = None,
    espn_uid: Optional[str] = None,
) -> int:
    base_name = kenpom_name.strip()
    espn = (espn_name or base_name).strip()
    ncaa = (ncaa_name or base_name).strip()

    cursor.execute(
        """
        INSERT INTO MBBTeams (KenPomName, EspnName, NcaaName, EspnID, EspnUID)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            TeamID = LAST_INSERT_ID(TeamID),
            KenPomName = VALUES(KenPomName),
            EspnName = VALUES(EspnName),
            NcaaName = VALUES(NcaaName),
            EspnID = COALESCE(VALUES(EspnID), EspnID),
            EspnUID = COALESCE(VALUES(EspnUID), EspnUID)
        """,
        (base_name, espn, ncaa, _normalize_name(espn_id), _normalize_name(espn_uid)),
    )
    return int(cursor.lastrowid)


def _find_team_id(
    cursor,
    kenpom_name: Optional[str] = None,
    espn_name: Optional[str] = None,
    ncaa_name: Optional[str] = None,
    espn_id: Optional[str] = None,
    espn_uid: Optional[str] = None,
) -> Optional[int]:
    fields = [
        ("EspnID", _normalize_name(espn_id)),
        ("EspnUID", _normalize_name(espn_uid)),
        ("KenPomName", _normalize_name(kenpom_name)),
        ("EspnName", _normalize_name(espn_name)),
        ("NcaaName", _normalize_name(ncaa_name)),
    ]

    for column, value in fields:
        if not value:
            continue
        cursor.execute(f"SELECT TeamID FROM MBBTeams WHERE {column} = %s", (value,))
        row = cursor.fetchone()
        if row:
            return int(row[0])

    return None


def uploadToSQL(arr, year: int):
    ensure_teamstats_fk_targets_mbbteams()

    if arr is None:
        return

    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        for item in arr:
            if not item:
                continue

            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                adjem = float(item.get("adjEM", 0.0))
                luck = float(item.get("luck", 0.0))
                sos = float(item.get("sos", 0.0))
                espn_name = item.get("espnName")
                ncaa_name = item.get("ncaaName")
                espn_id = item.get("espnID")
                espn_uid = item.get("espnUID")
            else:
                name = str(getattr(item, "name", "")).strip()
                adjem = float(getattr(item, "adjEM", 0.0))
                luck = float(getattr(item, "luck", 0.0))
                sos = float(getattr(item, "sos", 0.0))
                espn_name = getattr(item, "espnName", None)
                ncaa_name = getattr(item, "ncaaName", None)
                espn_id = getattr(item, "espnID", None)
                espn_uid = getattr(item, "espnUID", None)

            if not name:
                continue

            team_id = _upsert_team(
                cursor,
                name,
                espn_name=espn_name,
                ncaa_name=ncaa_name,
                espn_id=espn_id,
                espn_uid=espn_uid,
            )

            cursor.execute(
                """
                INSERT INTO TeamStatsByYear (TeamID, AdjEm, Luck, Sos, Year)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    AdjEm = VALUES(AdjEm),
                    Luck = VALUES(Luck),
                    Sos = VALUES(Sos)
                """,
                (team_id, adjem, luck, sos, int(year)),
            )

        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"uploadToSQL failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def downloadFromSQL(arr: List[team], year: int):
    if arr is None:
        return

    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT t.KenPomName, s.AdjEm, s.Luck, s.Sos
            FROM TeamStatsByYear s
            JOIN MBBTeams t ON t.TeamID = s.TeamID
            WHERE s.Year = %s
            ORDER BY t.KenPomName
            """,
            (int(year),),
        )

        for name, adjem, luck, sos in cursor.fetchall():
            arr.append(team(name, float(adjem), float(luck), float(sos)))
    except Error as e:
        raise RuntimeError(f"downloadFromSQL failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def getTeamStatsForYear(year: int) -> List[dict]:
    conn = getConnection(include_database=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                t.TeamID,
                t.KenPomName,
                t.EspnName,
                t.EspnID,
                t.EspnUID,
                t.NcaaName,
                s.AdjEm,
                s.Luck,
                s.Sos,
                s.Year
            FROM TeamStatsByYear s
            JOIN MBBTeams t ON t.TeamID = s.TeamID
            WHERE s.Year = %s
            ORDER BY t.KenPomName
            """,
            (int(year),),
        )
        return cursor.fetchall()
    except Error as e:
        raise RuntimeError(f"getTeamStatsForYear failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def upsertTeamNameMappings(mappings: Iterable[dict]):
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        for mapping in mappings:
            explicit_team_id = mapping.get("team_id")
            kenpom_name = _normalize_name(mapping.get("kenpom_name"))
            espn_name = _normalize_name(mapping.get("espn_name"))
            ncaa_name = _normalize_name(mapping.get("ncaa_name"))
            espn_id = _normalize_name(mapping.get("espn_id") or mapping.get("EspnID"))
            espn_uid = _normalize_name(mapping.get("espn_uid") or mapping.get("EspnUID"))

            if explicit_team_id is not None:
                team_id = int(explicit_team_id)
            else:
                team_id = _find_team_id(
                    cursor,
                    kenpom_name=kenpom_name,
                    espn_name=espn_name,
                    ncaa_name=ncaa_name,
                    espn_id=espn_id,
                    espn_uid=espn_uid,
                )

            if team_id is None:
                if not kenpom_name:
                    raise ValueError("Mapping requires kenpom_name when team does not already exist.")
                _upsert_team(
                    cursor,
                    kenpom_name,
                    espn_name=espn_name,
                    ncaa_name=ncaa_name,
                    espn_id=espn_id,
                    espn_uid=espn_uid,
                )
                continue

            cursor.execute(
                """
                UPDATE MBBTeams
                SET
                    KenPomName = COALESCE(%s, KenPomName),
                    EspnName = COALESCE(%s, EspnName),
                    NcaaName = COALESCE(%s, NcaaName),
                    EspnID = COALESCE(%s, EspnID),
                    EspnUID = COALESCE(%s, EspnUID)
                WHERE TeamID = %s
                """,
                (kenpom_name, espn_name, ncaa_name, espn_id, espn_uid, team_id),
            )

        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"upsertTeamNameMappings failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def getTeamsMissingEspnName(limit: int = 100) -> List[dict]:
    conn = getConnection(include_database=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT TeamID, KenPomName, EspnName, EspnID, EspnUID, NcaaName
            FROM MBBTeams
            WHERE EspnName IS NULL OR TRIM(EspnName) = '' OR EspnName = KenPomName
            ORDER BY KenPomName
            LIMIT %s
            """,
            (int(limit),),
        )
        return cursor.fetchall()
    except Error as e:
        raise RuntimeError(f"getTeamsMissingEspnName failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def upsertSeedsByYear(seed_rows: Iterable[dict], year: int):
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        for row in seed_rows:
            team_id = row.get("team_id")
            team_name = _normalize_name(row.get("team_name") or row.get("kenpom_name"))
            espn_name = _normalize_name(row.get("espn_name"))
            ncaa_name = _normalize_name(row.get("ncaa_name"))
            espn_id = _normalize_name(row.get("espn_id") or row.get("EspnID"))
            espn_uid = _normalize_name(row.get("espn_uid") or row.get("EspnUID"))

            if team_id is not None:
                resolved_team_id = int(team_id)
            else:
                resolved_team_id = _find_team_id(
                    cursor,
                    kenpom_name=team_name,
                    espn_name=espn_name,
                    ncaa_name=ncaa_name,
                    espn_id=espn_id,
                    espn_uid=espn_uid,
                )

            if resolved_team_id is None:
                if not team_name:
                    team_name = espn_name
                if not team_name:
                    raise ValueError("Unable to resolve team for seed row.")
                resolved_team_id = _upsert_team(
                    cursor,
                    team_name,
                    espn_name=espn_name,
                    ncaa_name=ncaa_name,
                    espn_id=espn_id,
                    espn_uid=espn_uid,
                )

            if row.get("division_id") is not None:
                division_id = int(row["division_id"])
            else:
                division_name = _normalize_name(row.get("division_name"))
                if not division_name:
                    raise ValueError("Seed row must include division_id or division_name.")
                division_id = DIVISION_NAME_TO_ID.get(division_name.lower())
                if division_id is None:
                    cursor.execute(
                        "SELECT DivisionID FROM Divisions WHERE DivisionName = %s",
                        (division_name,),
                    )
                    found = cursor.fetchone()
                    if not found:
                        raise ValueError(f"Unknown division: {division_name}")
                    division_id = int(found[0])

            cursor.execute(
                """
                INSERT INTO SeedByYear (TeamID, Seed, DivisionID, Year)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    Seed = VALUES(Seed),
                    DivisionID = VALUES(DivisionID)
                """,
                (resolved_team_id, int(row["seed"]), division_id, int(year)),
            )

        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"upsertSeedsByYear failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def getSeededBracket(year: int) -> Dict[str, List[dict]]:
    conn = getConnection(include_database=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                d.DivisionName,
                s.Seed,
                t.TeamID,
                t.KenPomName,
                t.EspnName,
                t.EspnID,
                t.EspnUID,
                t.NcaaName,
                y.AdjEm,
                y.Luck,
                y.Sos,
                y.Year
            FROM SeedByYear s
            JOIN Divisions d ON d.DivisionID = s.DivisionID
            JOIN MBBTeams t ON t.TeamID = s.TeamID
            LEFT JOIN TeamStatsByYear y ON y.TeamID = s.TeamID AND y.Year = s.Year
            WHERE s.Year = %s
            ORDER BY d.DivisionID, s.Seed
            """,
            (int(year),),
        )

        bracket: Dict[str, List[dict]] = {}
        for row in cursor.fetchall():
            div = row["DivisionName"]
            bracket.setdefault(div, []).append(row)
        return bracket
    except Error as e:
        raise RuntimeError(f"getSeededBracket failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def insertTournamentGame(team1_id: int, team2_id: int, team1_score: int, team2_score: int, year: int):
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO TournamentGames (Team1ID, Team2ID, Team1Score, Team2Score, Year)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (int(team1_id), int(team2_id), int(team1_score), int(team2_score), int(year)),
        )
        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"insertTournamentGame failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def upsertTournamentResult(team_name: str, year: int, round_reached: str):
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        team_id = _upsert_team(cursor, team_name)
        cursor.execute(
            """
            INSERT INTO TournamentResults (TeamID, Year, RoundReached)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE RoundReached = VALUES(RoundReached)
            """,
            (team_id, int(year), round_reached),
        )
        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"upsertTournamentResult failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def _name_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def getMBBTeams() -> List[dict]:
    conn = getConnection(include_database=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT TeamID, KenPomName, EspnID, NcaaName
            FROM MBBTeams
            ORDER BY KenPomName
            """
        )
        return cursor.fetchall()
    except Error as e:
        raise RuntimeError(f"getMBBTeams failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def updateTeamReferences(team_rows: Iterable[dict]):
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        for row in team_rows:
            team_id = int(row["TeamID"])
            kenpom_name = _normalize_name(row.get("KenPomName"))
            espn_id = _normalize_name(row.get("EspnID") or row.get("espn_id"))
            ncaa_name = _normalize_name(row.get("NcaaName"))

            if not kenpom_name:
                raise ValueError(f"TeamID {team_id} is missing KenPomName.")

            cursor.execute(
                """
                UPDATE MBBTeams
                SET KenPomName = %s, EspnID = %s, NcaaName = %s
                WHERE TeamID = %s
                """,
                (kenpom_name, espn_id, ncaa_name, team_id),
            )

        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"updateTeamReferences failed: {e}") from e
    finally:
        cursor.close()
        conn.close()


def replaceSeedsByYear(seed_rows: Iterable[dict], year: int):
    """Delete all seeds for *year* then insert the provided rows."""
    conn = getConnection(include_database=True)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM SeedByYear WHERE Year = %s", (int(year),))
        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"replaceSeedsByYear failed during delete: {e}") from e
    finally:
        cursor.close()
        conn.close()

    upsertSeedsByYear(seed_rows, year)


def fixTeamReferences(year: int) -> dict:
    """Reconcile missing ESPN references for teams seeded in *year*.

    Returns a summary dict with keys:
        matched, skipped_existing, unmatched, ambiguous,
        unmatched_rows, ambiguous_rows
    """
    from scraping.espnConnect import ESPNConnect

    conn = getConnection(include_database=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT t.TeamID, t.KenPomName, t.EspnName, t.EspnID
            FROM SeedByYear s
            JOIN MBBTeams t ON t.TeamID = s.TeamID
            WHERE s.Year = %s
            """,
            (int(year),),
        )
        seeded_teams = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    client = ESPNConnect()
    espn_teams = client.fetch_team_info(limit=500)

    espn_by_key: Dict[str, List[dict]] = {}
    for row in espn_teams:
        for name_source in (row.get("espn_name"), row.get("short_name"), row.get("display_name")):
            key = _name_key(name_source)
            if key:
                espn_by_key.setdefault(key, []).append(row)

    matched = 0
    skipped_existing = 0
    unmatched_rows: List[dict] = []
    ambiguous_rows: List[dict] = []

    mappings: List[dict] = []
    for team_row in seeded_teams:
        if team_row.get("EspnID"):
            skipped_existing += 1
            continue

        key = _name_key(team_row.get("KenPomName"))
        candidates = espn_by_key.get(key, [])

        if len(candidates) == 1:
            match = candidates[0]
            mappings.append(
                {
                    "team_id": team_row["TeamID"],
                    "kenpom_name": team_row.get("KenPomName"),
                    "espn_name": match.get("espn_name"),
                    "espn_id": str(match["espn_id"]) if match.get("espn_id") is not None else None,
                    "espn_uid": match.get("espn_uid"),
                    "ncaa_name": team_row.get("KenPomName"),
                }
            )
            matched += 1
        elif len(candidates) > 1:
            ambiguous_rows.append({"team": team_row.get("KenPomName"), "candidates": candidates})
        else:
            unmatched_rows.append({"team": team_row.get("KenPomName")})

    if mappings:
        upsertTeamNameMappings(mappings)

    return {
        "matched": matched,
        "skipped_existing": skipped_existing,
        "unmatched": len(unmatched_rows),
        "ambiguous": len(ambiguous_rows),
        "unmatched_rows": unmatched_rows,
        "ambiguous_rows": ambiguous_rows,
    }


def setupmbbteams(year: Optional[int] = None) -> dict:
    from datetime import datetime

    from scraping.espnConnect import ESPNConnect
    from scraping.kpScraper import scrapeSite, startDriver

    target_year = int(year or datetime.now().year)

    scraped_teams: List[team] = []
    driver = startDriver(target_year)
    try:
        scrapeSite(scraped_teams, driver)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    uploadToSQL(scraped_teams, target_year)

    client = ESPNConnect()
    espn_teams = client.fetch_team_info(limit=500)

    espn_lookup: Dict[str, dict] = {}
    for espn_row in espn_teams:
        for key_source in (espn_row.get("espn_name"), espn_row.get("short_name"), espn_row.get("display_name")):
            key = _name_key(key_source)
            if key and key not in espn_lookup:
                espn_lookup[key] = espn_row

    conn = getConnection(include_database=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT TeamID, KenPomName, NcaaName FROM MBBTeams ORDER BY KenPomName")
        current_rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    mappings: List[dict] = []
    for row in current_rows:
        key = _name_key(row.get("KenPomName"))
        match = espn_lookup.get(key)
        if not match:
            continue

        mappings.append(
            {
                "team_id": row["TeamID"],
                "kenpom_name": row.get("KenPomName"),
                "espn_name": match.get("espn_name"),
                "espn_id": str(match.get("espn_id")) if match.get("espn_id") is not None else None,
                "espn_uid": match.get("espn_uid"),
                "ncaa_name": row.get("NcaaName") or row.get("KenPomName"),
            }
        )

    if mappings:
        upsertTeamNameMappings(mappings)

    return {
        "year": target_year,
        "kenpom_rows": len(scraped_teams),
        "espn_rows": len(espn_teams),
        "mapped_rows": len(mappings),
    }
