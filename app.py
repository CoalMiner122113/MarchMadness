import json
import random
import uuid
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from app_logic.objDef import team as Team
from sql.sqlHandler import (
    getMBBTeams,
    getSeededBracket,
    getTeamStatsForYear,
    setupmbbteams,
    updateTeamReferences,
)


st.set_page_config(page_title="March Madness", page_icon=":basketball:", layout="wide")

SESSION_DIR = Path("session_data")
SESSION_DIR.mkdir(exist_ok=True)

DIVISION_ORDER = ["South", "East", "West", "Midwest"]
ROUND_NAMES = [
    "Round of 64",
    "Round of 32",
    "Sweet 16",
    "Elite 8",
    "Final Four",
    "Championship",
]
FIRST_ROUND_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]


st.markdown(
    """
    <style>
    .locked-round {
        background: #f2f2f2;
        color: #888;
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 8px;
    }
    .game-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.5rem;
        background: #fff;
    }
    .winner {
        color: #0b6b32;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _name_key(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _session_file() -> Path:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return SESSION_DIR / f"{st.session_state.session_id}.json"


def _sort_seed_rows(rows: List[dict]) -> List[dict]:
    division_index = {name: i for i, name in enumerate(DIVISION_ORDER)}
    return sorted(rows, key=lambda r: (division_index.get(r.get("division"), 999), int(r.get("seed", 999))))


def _load_seed_rows_from_sql(year: int) -> List[dict]:
    rows: List[dict] = []
    try:
        bracket = getSeededBracket(year)
    except Exception:
        bracket = {}

    if bracket:
        for division in DIVISION_ORDER:
            for item in bracket.get(division, []):
                rows.append(
                    {
                        "division": division,
                        "seed": int(item.get("Seed", 0)),
                        "team_id": item.get("TeamID"),
                        "team_name": item.get("KenPomName") or item.get("EspnName") or "",
                        "adj_em": float(item.get("AdjEm") or 0.0),
                        "luck": float(item.get("Luck") or 0.0),
                        "sos": float(item.get("Sos") or 0.0),
                    }
                )

    if rows:
        return _sort_seed_rows(rows)

    # Fallback: if no seeded rows in SQL, derive simple 1-16 buckets by AdjEm.
    try:
        stats = getTeamStatsForYear(year)
    except Exception:
        stats = []

    stats = sorted(stats, key=lambda r: float(r.get("AdjEm") or 0.0), reverse=True)
    for i, item in enumerate(stats[:64]):
        division = DIVISION_ORDER[(i // 16) % 4]
        seed = (i % 16) + 1
        rows.append(
            {
                "division": division,
                "seed": seed,
                "team_id": item.get("TeamID"),
                "team_name": item.get("KenPomName") or item.get("EspnName") or "",
                "adj_em": float(item.get("AdjEm") or 0.0),
                "luck": float(item.get("Luck") or 0.0),
                "sos": float(item.get("Sos") or 0.0),
            }
        )

    return _sort_seed_rows(rows)


def _init_session_payload(year: int) -> dict:
    base_rows = _load_seed_rows_from_sql(year)
    return {
        "year": int(year),
        "seeding": {
            "kenpom": base_rows,
            "bracketology": [dict(r) for r in base_rows],
        },
        "simulation": {
            "source": "kenpom",
            "completed_rounds": 0,
            "results": {},
            "winners": {},
        },
    }


def load_session_payload(year: int) -> dict:
    path = _session_file()
    if path.exists():
        payload = json.loads(path.read_text())
        if int(payload.get("year", 0)) == int(year):
            return payload

    payload = _init_session_payload(year)
    save_session_payload(payload)
    return payload


def save_session_payload(payload: dict):
    _session_file().write_text(json.dumps(payload, indent=2))


def _seed_map(rows: List[dict]) -> Dict[tuple, dict]:
    return {(r["division"], int(r["seed"])): r for r in rows}


def build_first_round_games(seed_rows: List[dict]) -> List[dict]:
    seed_lookup = _seed_map(seed_rows)
    games: List[dict] = []
    for division in DIVISION_ORDER:
        for seed1, seed2 in FIRST_ROUND_MATCHUPS:
            team1 = seed_lookup.get((division, seed1))
            team2 = seed_lookup.get((division, seed2))
            if team1 and team2:
                games.append({"division": division, "team1": team1, "team2": team2})
    return games


def _to_team_obj(entry: dict) -> Team:
    return Team(
        entry.get("team_name", "Unknown"),
        float(entry.get("adj_em") or 0.0),
        float(entry.get("luck") or 0.0),
        float(entry.get("sos") or 0.0),
    )


def _simulate_games(games: List[dict], round_num: int) -> tuple[List[dict], List[dict]]:
    results = []
    winners = []

    for game in games:
        t1_entry = game["team1"]
        t2_entry = game["team2"]
        t1 = _to_team_obj(t1_entry)
        t2 = _to_team_obj(t2_entry)

        t1.versus(t2, round_num)
        p1 = max(0.0, min(1.0, t1.probability))

        if random.random() <= p1:
            winner_entry, loser_entry, win_prob = t1_entry, t2_entry, p1
        else:
            winner_entry, loser_entry, win_prob = t2_entry, t1_entry, 1.0 - p1

        results.append(
            {
                "division": game.get("division", ""),
                "team1": t1_entry.get("team_name"),
                "team2": t2_entry.get("team_name"),
                "winner": winner_entry.get("team_name"),
                "loser": loser_entry.get("team_name"),
                "win_prob": round(float(win_prob), 4),
            }
        )
        winners.append({"division": game.get("division", ""), "team": winner_entry})

    return results, winners


def _build_next_games_from_winners(round_index: int, winners: List[dict]) -> List[dict]:
    # round_index: 1=>Round32, 2=>Sweet16, 3=>Elite8, 4=>FinalFour, 5=>Championship
    games: List[dict] = []

    if round_index in (1, 2, 3):
        grouped: Dict[str, List[dict]] = {d: [] for d in DIVISION_ORDER}
        for row in winners:
            grouped.setdefault(row["division"], []).append(row["team"])

        for division in DIVISION_ORDER:
            teams = grouped.get(division, [])
            for i in range(0, len(teams), 2):
                if i + 1 < len(teams):
                    games.append({"division": division, "team1": teams[i], "team2": teams[i + 1]})
        return games

    if round_index == 4:
        champs = {row["division"]: row["team"] for row in winners}
        east = champs.get("East")
        west = champs.get("West")
        south = champs.get("South")
        midwest = champs.get("Midwest")
        if east and west:
            games.append({"division": "Final Four", "team1": east, "team2": west})
        if south and midwest:
            games.append({"division": "Final Four", "team1": south, "team2": midwest})
        return games

    if round_index == 5:
        finalists = [row["team"] for row in winners]
        if len(finalists) >= 2:
            games.append({"division": "Championship", "team1": finalists[0], "team2": finalists[1]})
        return games

    return games


def _pending_games(payload: dict, source: str, round_index: int) -> List[dict]:
    winners = payload["simulation"].get("winners", {})

    if round_index == 0:
        return build_first_round_games(payload["seeding"][source])

    prev_key = ROUND_NAMES[round_index - 1]
    prev_winners = winners.get(prev_key, [])
    return _build_next_games_from_winners(round_index, prev_winners)


def _games_by_division(games: List[dict]) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for game in games:
        div = game.get("division", "Other")
        grouped.setdefault(div, []).append(game)

    ordered: Dict[str, List[dict]] = {}
    for div in DIVISION_ORDER:
        if div in grouped:
            ordered[div] = grouped.pop(div)
    for div, div_games in grouped.items():
        ordered[div] = div_games
    return ordered


def _render_games_from_results(results: List[dict]):
    if not results:
        st.info("No games to display yet.")
        return

    for division, div_games in _games_by_division(results).items():
        with st.expander(division.upper(), expanded=False):
            for i, game in enumerate(div_games, start=1):
                st.markdown(
                    f"""
                    <div class="game-card">
                        <div><b>Game {i}:</b> <b>{game['team1']}</b> vs <b>{game['team2']}</b></div>
                        <div class="winner">Winner: {game['winner']} ({game['win_prob']:.1%})</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_games_preview(games: List[dict]):
    if not games:
        st.info("No matchups available for this round.")
        return

    for division, div_games in _games_by_division(games).items():
        with st.expander(division.upper(), expanded=False):
            for i, game in enumerate(div_games, start=1):
                st.markdown(
                    f"""
                    <div class="game-card">
                        <div><b>Game {i}:</b> <b>{game['team1']['team_name']}</b> vs <b>{game['team2']['team_name']}</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def view_seeding_page(payload: dict):
    st.subheader("View Seeding")
    source_label = st.radio("Projection Source", ["KenPom", "Bracketology"], horizontal=True)
    source_key = "kenpom" if source_label == "KenPom" else "bracketology"

    rows = _sort_seed_rows(payload["seeding"][source_key])
    editable_df = pd.DataFrame(rows)[["division", "seed", "team_name", "adj_em", "luck", "sos"]]
    edited_df = st.data_editor(editable_df, use_container_width=True, hide_index=True, key=f"seed_editor_{source_key}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Seeding Edits", key=f"save_seed_{source_key}"):
            payload["seeding"][source_key] = _sort_seed_rows(edited_df.to_dict(orient="records"))
            payload["simulation"] = {"source": source_key, "completed_rounds": 0, "results": {}, "winners": {}}
            save_session_payload(payload)
            st.success("Seeding saved to this session file. Simulation reset for this source.")
    with c2:
        if st.button("Reload Seeding From SQL", key=f"reload_seed_{source_key}"):
            fresh = _load_seed_rows_from_sql(int(payload["year"]))
            payload["seeding"][source_key] = fresh
            payload["simulation"] = {"source": source_key, "completed_rounds": 0, "results": {}, "winners": {}}
            save_session_payload(payload)
            st.success("Reloaded from SQL and reset simulation.")


def run_simulation_page(payload: dict):
    st.subheader("Run Simulation")
    source_label = st.radio("Use Seeding From", ["KenPom", "Bracketology"], horizontal=True, key="sim_source")
    source_key = "kenpom" if source_label == "KenPom" else "bracketology"
    payload["simulation"]["source"] = source_key

    completed = int(payload["simulation"].get("completed_rounds", 0))
    tabs = st.tabs(ROUND_NAMES)

    for i, round_name in enumerate(ROUND_NAMES):
        with tabs[i]:
            round_results = payload["simulation"].get("results", {}).get(round_name)

            if i < completed and round_results:
                _render_games_from_results(round_results)
                continue

            if i > completed:
                st.markdown(
                    """
                    <div class="locked-round">
                        This round is locked. Calculate the previous round to unlock it.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                continue

            # i == completed: pending active round
            pending_games = _pending_games(payload, source_key, i)
            _render_games_preview(pending_games)

            if st.button(f"Calculate {round_name}", key=f"calc_{i}"):
                results, winners = _simulate_games(pending_games, i + 1)
                payload["simulation"].setdefault("results", {})[round_name] = results
                payload["simulation"].setdefault("winners", {})[round_name] = winners
                payload["simulation"]["completed_rounds"] = min(6, completed + 1)
                save_session_payload(payload)
                st.rerun()


def past_tournaments_page():
    st.subheader("Past Tournaments")
    st.info("Historical tournament workflows can be added here. This section is scaffolded for the new hierarchy.")


def admin_update_team_references_page():
    st.subheader("Update Team References")
    st.caption("Edit team identity references in MBBTeams and run setup to refresh mappings.")

    year = st.number_input("Season Year", min_value=2002, max_value=2100, value=2026, step=1, key="admin_year")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Setup MBBTeams (KenPom + ESPN)", key="admin_setup_mbbteams"):
            with st.spinner("Running setupmbbteams..."):
                try:
                    summary = setupmbbteams(int(year))
                    st.success(
                        f"Setup complete for {summary['year']}: KenPom rows={summary['kenpom_rows']}, ESPN rows={summary['espn_rows']}, mapped rows={summary['mapped_rows']}"
                    )
                except Exception as exc:
                    st.error(f"Setup failed: {exc}")

    try:
        rows = getMBBTeams()
    except Exception as exc:
        st.error(f"Failed to load MBBTeams: {exc}")
        return

    if not rows:
        st.info("No team rows found in MBBTeams.")
        return

    df = pd.DataFrame(rows)
    cols = [c for c in ["TeamID", "KenPomName", "EspnID", "NcaaName"] if c in df.columns]
    editable_df = df[cols].copy()

    edited_df = st.data_editor(
        editable_df,
        use_container_width=True,
        hide_index=True,
        disabled=["TeamID"],
        key="admin_team_reference_editor",
    )

    with c2:
        if st.button("Save Team Reference Changes", key="admin_save_team_refs"):
            try:
                updateTeamReferences(edited_df.to_dict(orient="records"))
                st.success("Team references saved.")
            except Exception as exc:
                st.error(f"Save failed: {exc}")


st.title("March Madness")
menu = st.sidebar.selectbox("Hierarchy", ["March Madness", "Past Tournaments", "Admin"])

if menu == "March Madness":
    year = 2026
    payload = load_session_payload(year)
    subpage = st.sidebar.selectbox("March Madness 2026", ["View Seeding", "Run Simulation"])

    st.caption(f"Session file: {str(_session_file())}")

    if subpage == "View Seeding":
        view_seeding_page(payload)
    else:
        run_simulation_page(payload)
elif menu == "Past Tournaments":
    past_tournaments_page()
elif menu == "Admin":
    admin_subpage = st.sidebar.selectbox("Admin", ["Update Team References"])
    if admin_subpage == "Update Team References":
        admin_update_team_references_page()
