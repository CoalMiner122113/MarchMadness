import json
import math
import random
import uuid
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from app_logic.objDef import team as Team
from scraping.espnConnect import ESPNConnect
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


def _matchup_key(division: str, team1: str, team2: str) -> str:
    return f"{division}|{_name_key(team1)}|{_name_key(team2)}"


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


def _load_espn_probabilities(year: int) -> List[dict]:
    try:
        client = ESPNConnect()
        return client.fetch_matchup_probabilities(year)
    except Exception:
        return []


def _lookup_espn_probability(prob_rows: List[dict], team1: str, team2: str) -> float:
    k1 = _name_key(team1)
    k2 = _name_key(team2)

    for row in prob_rows:
        a = _name_key(row.get("team1", ""))
        b = _name_key(row.get("team2", ""))
        p = float(row.get("team1_probability", 50.0))
        if a == k1 and b == k2:
            return round(max(0.0, min(100.0, p)), 2)
        if a == k2 and b == k1:
            return round(max(0.0, min(100.0, 100.0 - p)), 2)

    return 50.0


def _kenpom_strength(entry: dict) -> float:
    adj_em = float(entry.get("adj_em") or 0.0)
    sos = float(entry.get("sos") or 0.0)
    luck = float(entry.get("luck") or 0.0)
    sos_component = math.copysign(math.sqrt(abs(sos)), sos) if sos != 0 else 0.0
    return adj_em + 0.35 * sos_component + 2.0 * luck


def _lookup_kenpom_probability(team1_entry: dict, team2_entry: dict) -> float:
    s1 = _kenpom_strength(team1_entry)
    s2 = _kenpom_strength(team2_entry)
    diff = s1 - s2
    p = 1.0 / (1.0 + math.exp(-diff / 6.0))
    return round(max(0.0, min(100.0, p * 100.0)), 2)


def _init_session_payload(year: int) -> dict:
    base_rows = _load_seed_rows_from_sql(year)
    return {
        "year": int(year),
        "seeding": {
            "kenpom": base_rows,
            "bracketology": [dict(r) for r in base_rows],
        },
        "espn_probabilities": _load_espn_probabilities(year),
        "simulation": {
            "source": "kenpom",
            "default_probability_source": "ESPN Probability",
            "completed_rounds": 0,
            "results": {},
            "winners": {},
            "round_inputs": {},
        },
    }


def load_session_payload(year: int) -> dict:
    path = _session_file()
    if path.exists():
        payload = json.loads(path.read_text())
        if int(payload.get("year", 0)) == int(year):
            payload.setdefault("espn_probabilities", _load_espn_probabilities(year))
            sim = payload.setdefault("simulation", {})
            sim.setdefault("source", "kenpom")
            sim.setdefault("default_probability_source", "ESPN Probability")
            sim.setdefault("completed_rounds", 0)
            sim.setdefault("results", {})
            sim.setdefault("winners", {})
            sim.setdefault("round_inputs", {})
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

        team1_probs = game.get("team1_probs", {})
        team2_probs = game.get("team2_probs", {})

        sim1 = max(0.0, min(100.0, float(team1_probs.get("simulation_probability", 50.0))))
        sim2 = max(0.0, min(100.0, float(team2_probs.get("simulation_probability", 50.0))))
        denom = sim1 + sim2
        p1 = (sim1 / denom) if denom > 0 else 0.5

        if random.random() <= p1:
            winner_entry, loser_entry = t1_entry, t2_entry
            winner_probs = team1_probs
        else:
            winner_entry, loser_entry = t2_entry, t1_entry
            winner_probs = team2_probs

        results.append(
            {
                "division": game.get("division", ""),
                "team1": t1_entry.get("team_name"),
                "team2": t2_entry.get("team_name"),
                "winner": winner_entry.get("team_name"),
                "loser": loser_entry.get("team_name"),
                "winner_espn_probability": round(float(winner_probs.get("espn_probability", 50.0)), 2),
                "winner_kenpom_probability": round(float(winner_probs.get("kenpom_probability", 50.0)), 2),
                "winner_simulation_probability": round(float(winner_probs.get("simulation_probability", 50.0)), 2),
                "winner_moneyline": int(round(float(winner_probs.get("moneyline", -100)))),
            }
        )
        winners.append({"division": game.get("division", ""), "team": winner_entry})

    return results, winners


def _build_next_games_from_winners(round_index: int, winners: List[dict]) -> List[dict]:
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
                        <div class="winner">Winner: {game['winner']}</div>
                        <div>Winner ESPN: {float(game['winner_espn_probability']):.2f}% | Winner KenPom: {float(game['winner_kenpom_probability']):.2f}%</div>
                        <div>Winner Simulation: {float(game['winner_simulation_probability']):.2f}% | Winner Moneyline: {int(game['winner_moneyline'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_probability_editor(payload: dict, round_name: str, pending_games: List[dict], default_source: str) -> List[dict]:
    prob_rows = payload.get("espn_probabilities", [])
    existing = payload["simulation"].setdefault("round_inputs", {}).get(round_name, [])
    existing_map = {r.get("row_key"): r for r in existing}

    edited_rows: List[dict] = []

    for division, div_games in _games_by_division(pending_games).items():
        with st.expander(division.upper(), expanded=False):
            for game_idx, game in enumerate(div_games, start=1):
                team1_name = game["team1"]["team_name"]
                team2_name = game["team2"]["team_name"]
                matchup_key = _matchup_key(division, team1_name, team2_name)

                team_specs = [
                    (game["team1"], game["team2"], team1_name),
                    (game["team2"], game["team1"], team2_name),
                ]

                row_models = []
                for team_entry, opponent_entry, team_name in team_specs:
                    row_key = f"{matchup_key}|{_name_key(team_name)}"
                    espn_prob = _lookup_espn_probability(prob_rows, team_name, opponent_entry["team_name"])
                    kenpom_prob = _lookup_kenpom_probability(team_entry, opponent_entry)

                    existing_row = existing_map.get(row_key, {})
                    default_sim = espn_prob if default_source == "ESPN Probability" else kenpom_prob
                    sim_prob = existing_row.get("simulation_probability", default_sim)
                    moneyline = existing_row.get("moneyline", -100)

                    row_models.append(
                        {
                            "row_key": row_key,
                            "matchup_key": matchup_key,
                            "division": division,
                            "team": team_name,
                            "espn_probability": round(float(espn_prob), 2),
                            "kenpom_probability": round(float(kenpom_prob), 2),
                            "moneyline": int(round(float(moneyline))),
                            "simulation_probability": round(float(sim_prob), 2),
                        }
                    )

                shade = "#f3f7ff" if game_idx % 2 == 1 else "#f4fbf2"
                st.markdown(
                    f"<div style='background:{shade};padding:6px 10px;border-radius:6px;border:1px solid #d9dee8;'><b>Game {game_idx}</b>: {team1_name} vs {team2_name}</div>",
                    unsafe_allow_html=True,
                )

                view_df = pd.DataFrame(row_models)[
                    ["team", "espn_probability", "kenpom_probability", "moneyline", "simulation_probability"]
                ].copy()

                edited_view = st.data_editor(
                    view_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["team", "espn_probability", "kenpom_probability", "moneyline"],
                    column_config={
                        "team": "Team",
                        "espn_probability": st.column_config.NumberColumn(
                            "ESPN Probability", min_value=0.0, max_value=100.0, format="%.2f%%"
                        ),
                        "kenpom_probability": st.column_config.NumberColumn(
                            "KenPom Probability", min_value=0.0, max_value=100.0, format="%.2f%%"
                        ),
                        "moneyline": st.column_config.NumberColumn("Moneyline", step=1, format="%d"),
                        "simulation_probability": st.column_config.NumberColumn(
                            "Simulation Probability", min_value=0.0, max_value=100.0, step=0.01, format="%.2f%%"
                        ),
                    },
                    key=f"prob_editor_{round_name}_{_name_key(division)}_{game_idx}",
                )

                team1_sim = 50.0
                if len(edited_view.index) > 0:
                    try:
                        team1_sim = float(edited_view.iloc[0]["simulation_probability"])
                    except Exception:
                        team1_sim = float(row_models[0]["simulation_probability"])
                team1_sim = round(max(0.0, min(100.0, team1_sim)), 2)
                team2_sim = round(100.0 - team1_sim, 2)

                # Force complementary display values for this matchup before persisting.
                if len(edited_view.index) > 0:
                    edited_view.at[edited_view.index[0], "simulation_probability"] = team1_sim
                if len(edited_view.index) > 1:
                    edited_view.at[edited_view.index[1], "simulation_probability"] = team2_sim

                for i, row in edited_view.iterrows():
                    base = row_models[i]
                    sim_value = team1_sim if i == 0 else team2_sim
                    edited_rows.append(
                        {
                            "row_key": base["row_key"],
                            "matchup_key": base["matchup_key"],
                            "division": base["division"],
                            "team": base["team"],
                            "espn_probability": round(float(base["espn_probability"]), 2),
                            "kenpom_probability": round(float(base["kenpom_probability"]), 2),
                            "moneyline": int(round(float(base["moneyline"]))),
                            "simulation_probability": round(float(sim_value), 2),
                        }
                    )

    payload["simulation"]["round_inputs"][round_name] = edited_rows
    save_session_payload(payload)
    return edited_rows


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
            payload["simulation"] = {
                "source": source_key,
                "default_probability_source": payload["simulation"].get("default_probability_source", "ESPN Probability"),
                "completed_rounds": 0,
                "results": {},
                "winners": {},
                "round_inputs": {},
            }
            save_session_payload(payload)
            st.success("Seeding saved to this session file. Simulation reset for this source.")
    with c2:
        if st.button("Reload Seeding From SQL", key=f"reload_seed_{source_key}"):
            fresh = _load_seed_rows_from_sql(int(payload["year"]))
            payload["seeding"][source_key] = fresh
            payload["simulation"] = {
                "source": source_key,
                "default_probability_source": payload["simulation"].get("default_probability_source", "ESPN Probability"),
                "completed_rounds": 0,
                "results": {},
                "winners": {},
                "round_inputs": {},
            }
            payload["espn_probabilities"] = _load_espn_probabilities(int(payload["year"]))
            save_session_payload(payload)
            st.success("Reloaded from SQL and reset simulation.")


def run_simulation_page(payload: dict):
    st.subheader("Run Simulation")
    source_label = st.radio("Use Seeding From", ["KenPom", "Bracketology"], horizontal=True, key="sim_source")
    source_key = "kenpom" if source_label == "KenPom" else "bracketology"
    payload["simulation"]["source"] = source_key

    default_source = st.selectbox(
        "Default Simulation Probability",
        ["ESPN Probability", "KenPom Probability"],
        index=0 if payload["simulation"].get("default_probability_source", "ESPN Probability") == "ESPN Probability" else 1,
        key="sim_default_prob_source",
    )
    payload["simulation"]["default_probability_source"] = default_source

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

            pending_games = _pending_games(payload, source_key, i)
            edited_prob_rows = _render_probability_editor(payload, round_name, pending_games, default_source)

            prob_map = {r["row_key"]: r for r in edited_prob_rows}
            calc_games = []
            for g in pending_games:
                t1 = g["team1"]["team_name"]
                t2 = g["team2"]["team_name"]
                matchup_key = _matchup_key(g["division"], t1, t2)
                r1 = prob_map.get(f"{matchup_key}|{_name_key(t1)}", {})
                r2 = prob_map.get(f"{matchup_key}|{_name_key(t2)}", {})

                calc_games.append(
                    {
                        **g,
                        "team1_probs": {
                            "espn_probability": float(r1.get("espn_probability", 50.0)),
                            "kenpom_probability": float(r1.get("kenpom_probability", 50.0)),
                            "simulation_probability": float(r1.get("simulation_probability", 50.0)),
                            "moneyline": float(r1.get("moneyline", -100)),
                        },
                        "team2_probs": {
                            "espn_probability": float(r2.get("espn_probability", 50.0)),
                            "kenpom_probability": float(r2.get("kenpom_probability", 50.0)),
                            "simulation_probability": float(r2.get("simulation_probability", 50.0)),
                            "moneyline": float(r2.get("moneyline", -100)),
                        },
                    }
                )

            if st.button(f"Calculate {round_name}", key=f"calc_{i}"):
                results, winners = _simulate_games(calc_games, i + 1)
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
