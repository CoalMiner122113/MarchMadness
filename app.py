import json
import math
import random
import uuid
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from app_logic.objDef import team as Team
from scraping.espnConnect import ESPNConnect
from sql.sqlHandler import (
    fixTeamReferences,
    getMBBTeams,
    getSeededBracket,
    getTeamStatsForYear,
    replaceSeedsByYear,
    setupmbbteams,
    updateTeamReferences,
    upsertSeedsByYear,
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


@st.cache_data(show_spinner=False)
def _team_option_rows(year: int) -> List[dict]:
    teams = getMBBTeams()
    stats_by_team = {row.get("TeamID"): row for row in getTeamStatsForYear(year)}
    option_rows: List[dict] = []

    for row in teams:
        team_id = row.get("TeamID")
        stats = stats_by_team.get(team_id, {})
        team_name = row.get("KenPomName") or row.get("EspnName") or row.get("NcaaName") or f"Team {team_id}"
        option_rows.append(
            {
                "team_id": team_id,
                "team_name": team_name,
                "espn_id": row.get("EspnID"),
                "espn_name": row.get("EspnName"),
                "ncaa_name": row.get("NcaaName"),
                "adj_em": float(stats.get("AdjEm") or 0.0),
                "luck": float(stats.get("Luck") or 0.0),
                "sos": float(stats.get("Sos") or 0.0),
            }
        )

    return sorted(option_rows, key=lambda r: r["team_name"].lower())


def _team_option_label(option: Optional[dict]) -> str:
    if not option:
        return "Select team"
    team_name = option.get("team_name") or "Unknown"
    espn_id = option.get("espn_id")
    return f"{team_name} [{espn_id}]" if espn_id else team_name


def _seed_row_from_option(division: str, seed: int, option: dict) -> dict:
    return {
        "division": division,
        "seed": int(seed),
        "team_id": option.get("team_id"),
        "team_name": option.get("team_name") or "",
        "adj_em": float(option.get("adj_em") or 0.0),
        "luck": float(option.get("luck") or 0.0),
        "sos": float(option.get("sos") or 0.0),
    }


def _reset_simulation_for_source(payload: dict, source_key: str):
    payload["simulation"] = {
        "source": source_key,
        "default_probability_source": payload["simulation"].get("default_probability_source", "ESPN Probability"),
        "completed_rounds": 0,
        "results": {},
        "winners": {},
        "round_inputs": {},
    }


def _seed_editor_revision(source_key: str) -> int:
    state_key = f"seed_editor_revision_{source_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    return int(st.session_state[state_key])


def _bump_seed_editor_revision(source_key: str):
    state_key = f"seed_editor_revision_{source_key}"
    st.session_state[state_key] = _seed_editor_revision(source_key) + 1


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


def _clamp_probability(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


def _sync_probability_pair(changed_key: str, other_key: str):
    changed_value = _clamp_probability(st.session_state.get(changed_key, 50.0))
    st.session_state[changed_key] = changed_value
    st.session_state[other_key] = round(100.0 - changed_value, 2)


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
    prior_rows = payload["simulation"].setdefault("round_inputs", {}).get(round_name, [])
    existing_map = {r.get("row_key"): r for r in prior_rows}

    edited_rows: List[dict] = []
    did_change = False

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
                            "seed": int(team_entry.get("seed", 0) or 0),
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

                header_cols = st.columns([0.8, 2.2, 1.2, 1.2, 1.0, 1.6])
                header_cols[0].markdown("**Seed**")
                header_cols[1].markdown("**Team**")
                header_cols[2].markdown("**ESPN**")
                header_cols[3].markdown("**KenPom**")
                header_cols[4].markdown("**Moneyline**")
                header_cols[5].markdown("**Simulation Probability**")

                team1_default = round(float(row_models[0]["simulation_probability"]), 2)
                team2_default = round(float(row_models[1]["simulation_probability"]), 2)
                team1_key = f"sim_prob_{round_name}_{_name_key(division)}_{game_idx}_1"
                team2_key = f"sim_prob_{round_name}_{_name_key(division)}_{game_idx}_2"

                if team1_key not in st.session_state:
                    st.session_state[team1_key] = team1_default
                if team2_key not in st.session_state:
                    st.session_state[team2_key] = team2_default

                row1_cols = st.columns([0.8, 2.2, 1.2, 1.2, 1.0, 1.6])
                row1_cols[0].write(str(row_models[0]["seed"]))
                row1_cols[1].write(row_models[0]["team"])
                row1_cols[2].write(f'{row_models[0]["espn_probability"]:.2f}%')
                row1_cols[3].write(f'{row_models[0]["kenpom_probability"]:.2f}%')
                row1_cols[4].write(str(row_models[0]["moneyline"]))
                team1_sim = row1_cols[5].number_input(
                    f"Team 1 Simulation Probability {division} Game {game_idx}",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.01,
                    format="%.2f",
                    key=team1_key,
                    label_visibility="collapsed",
                    on_change=_sync_probability_pair,
                    args=(team1_key, team2_key),
                )

                row2_cols = st.columns([0.8, 2.2, 1.2, 1.2, 1.0, 1.6])
                row2_cols[0].write(str(row_models[1]["seed"]))
                row2_cols[1].write(row_models[1]["team"])
                row2_cols[2].write(f'{row_models[1]["espn_probability"]:.2f}%')
                row2_cols[3].write(f'{row_models[1]["kenpom_probability"]:.2f}%')
                row2_cols[4].write(str(row_models[1]["moneyline"]))
                team2_sim = row2_cols[5].number_input(
                    f"Team 2 Simulation Probability {division} Game {game_idx}",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.01,
                    format="%.2f",
                    key=team2_key,
                    label_visibility="collapsed",
                    on_change=_sync_probability_pair,
                    args=(team2_key, team1_key),
                )

                team1_sim = _clamp_probability(team1_sim)
                team2_sim = _clamp_probability(team2_sim)
                changed1 = team1_sim != team1_default
                changed2 = team2_sim != team2_default

                if changed1 or changed2:
                    did_change = True

                for i, base in enumerate(row_models):
                    sim_value = team1_sim if i == 0 else team2_sim
                    edited_rows.append(
                        {
                            "row_key": base["row_key"],
                            "matchup_key": base["matchup_key"],
                            "division": base["division"],
                            "team": base["team"],
                            "seed": int(base["seed"]),
                            "espn_probability": round(float(base["espn_probability"]), 2),
                            "kenpom_probability": round(float(base["kenpom_probability"]), 2),
                            "moneyline": int(round(float(base["moneyline"]))),
                            "simulation_probability": round(float(sim_value), 2),
                        }
                    )

    payload["simulation"]["round_inputs"][round_name] = edited_rows
    if did_change or edited_rows != prior_rows:
        save_session_payload(payload)
    return edited_rows


def _reset_simulation_from_round(payload: dict, start_round_index: int):
    sim = payload["simulation"]
    round_names_to_clear = ROUND_NAMES[start_round_index:]

    for round_name in round_names_to_clear:
        sim.setdefault("results", {}).pop(round_name, None)
        sim.setdefault("winners", {}).pop(round_name, None)
        sim.setdefault("round_inputs", {}).pop(round_name, None)

    sim["completed_rounds"] = start_round_index


def view_seeding_page(payload: dict):
    st.subheader("View Seeding")
    source_label = st.radio("Projection Source", ["KenPom", "Bracketology"], horizontal=True)
    source_key = "kenpom" if source_label == "KenPom" else "bracketology"

    year = int(payload["year"])
    option_rows = _team_option_rows(year)
    option_by_id = {row["team_id"]: row for row in option_rows}
    option_values = [None] + [row["team_id"] for row in option_rows]
    rows = _sort_seed_rows(payload["seeding"][source_key])
    slot_map = _seed_map(rows)
    revision = _seed_editor_revision(source_key)

    updated_rows: List[dict] = []
    selected_team_ids: List[int] = []
    missing_slots: List[str] = []

    for division in DIVISION_ORDER:
        st.markdown(f"### {division}")
        for game_idx, (seed1, seed2) in enumerate(FIRST_ROUND_MATCHUPS, start=1):
            st.markdown(
                f"<div style='background:#f7f7f9;padding:6px 10px;border-radius:6px;border:1px solid #d9dee8;'><b>Game {game_idx}</b>: {seed1} vs {seed2}</div>",
                unsafe_allow_html=True,
            )

            slot1 = slot_map.get((division, seed1), {})
            slot2 = slot_map.get((division, seed2), {})
            key1 = f"seed_select_{source_key}_{revision}_{_name_key(division)}_{seed1}"
            key2 = f"seed_select_{source_key}_{revision}_{_name_key(division)}_{seed2}"

            cols = st.columns([0.7, 4.3, 0.7, 4.3])
            cols[0].markdown(f"**{seed1}**")
            selected_team1 = cols[1].selectbox(
                f"{division} Seed {seed1}",
                options=option_values,
                index=option_values.index(slot1.get("team_id")) if slot1.get("team_id") in option_by_id else 0,
                format_func=lambda team_id: _team_option_label(option_by_id.get(team_id)),
                key=key1,
                label_visibility="collapsed",
            )
            cols[2].markdown(f"**{seed2}**")
            selected_team2 = cols[3].selectbox(
                f"{division} Seed {seed2}",
                options=option_values,
                index=option_values.index(slot2.get("team_id")) if slot2.get("team_id") in option_by_id else 0,
                format_func=lambda team_id: _team_option_label(option_by_id.get(team_id)),
                key=key2,
                label_visibility="collapsed",
            )

            for seed, selected_team_id in ((seed1, selected_team1), (seed2, selected_team2)):
                selected_option = option_by_id.get(selected_team_id)
                if not selected_option:
                    missing_slots.append(f"{division} {seed}")
                    continue
                selected_team_ids.append(int(selected_team_id))
                updated_rows.append(_seed_row_from_option(division, seed, selected_option))

    duplicate_counts = Counter(selected_team_ids)
    duplicate_ids = [team_id for team_id, count in duplicate_counts.items() if count > 1]
    duplicate_names = [_team_option_label(option_by_id.get(team_id)) for team_id in duplicate_ids]

    if missing_slots:
        st.warning(f"Missing team assignments: {', '.join(missing_slots)}")
    if duplicate_names:
        st.error(f"Duplicate teams selected: {', '.join(sorted(duplicate_names))}")

    def _validate_seed_editor() -> bool:
        if missing_slots:
            st.error("Assign a team to every bracket slot before saving.")
            return False
        if duplicate_names:
            st.error("Each team can only appear once in the bracket. Resolve duplicates before saving.")
            return False
        return True

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Save Seeding Edits", key=f"save_seed_{source_key}"):
            if _validate_seed_editor():
                payload["seeding"][source_key] = _sort_seed_rows(updated_rows)
                _reset_simulation_for_source(payload, source_key)
                save_session_payload(payload)
                st.success("Seeding saved to this session file. Simulation reset for this source.")
    with c2:
        if st.button("Save Seeding To SQL", key=f"save_seed_sql_{source_key}"):
            if _validate_seed_editor():
                normalized_rows = _sort_seed_rows(updated_rows)
                try:
                    replaceSeedsByYear(normalized_rows, year)
                except Exception as exc:
                    st.error(f"Save to SQL failed: {exc}")
                else:
                    payload["seeding"][source_key] = normalized_rows
                    _reset_simulation_for_source(payload, source_key)
                    save_session_payload(payload)
                    st.success(f"Saved {len(normalized_rows)} seed assignments to SQL for {year}.")
    with c3:
        if st.button("Reload Seeding From SQL", key=f"reload_seed_{source_key}"):
            fresh = _load_seed_rows_from_sql(year)
            payload["seeding"][source_key] = fresh
            _reset_simulation_for_source(payload, source_key)
            payload["espn_probabilities"] = _load_espn_probabilities(year)
            save_session_payload(payload)
            _bump_seed_editor_revision(source_key)
            st.rerun()


def run_simulation_page(payload: dict):
    st.subheader("Run Simulation")
    source_label = st.radio("Use Seeding From", ["KenPom", "Bracketology"], horizontal=True, key="sim_source")
    source_key = "kenpom" if source_label == "KenPom" else "bracketology"
    payload["simulation"]["source"] = source_key

    prior_default_source = payload["simulation"].get("default_probability_source", "ESPN Probability")
    default_source = st.selectbox(
        "Default Simulation Probability",
        ["ESPN Probability", "KenPom Probability"],
        index=0 if prior_default_source == "ESPN Probability" else 1,
        key="sim_default_prob_source",
    )
    payload["simulation"]["default_probability_source"] = default_source

    if default_source != prior_default_source:
        payload["simulation"]["round_inputs"] = {}
        save_session_payload(payload)
        st.rerun()

    completed = int(payload["simulation"].get("completed_rounds", 0))
    tabs = st.tabs(ROUND_NAMES)

    for i, round_name in enumerate(ROUND_NAMES):
        with tabs[i]:
            round_results = payload["simulation"].get("results", {}).get(round_name)
            round_has_results = bool(round_results)

            action_cols = st.columns([1, 1, 5])
            with action_cols[0]:
                calculate_clicked = st.button(f"Calculate {round_name}", key=f"calc_{i}", disabled=i > completed)
            with action_cols[1]:
                reset_clicked = st.button(f"Reset {round_name}", key=f"reset_{i}", disabled=not round_has_results)

            if reset_clicked:
                _reset_simulation_from_round(payload, i)
                save_session_payload(payload)
                st.rerun()

            if i < completed and round_has_results:
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

            if calculate_clicked:
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

    if "team_reference_fix_result" not in st.session_state:
        st.session_state.team_reference_fix_result = None

    c1, c2, c3 = st.columns(3)
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
    with c2:
        if st.button("Fix team references", key="admin_fix_team_refs"):
            with st.spinner("Reconciling missing ESPN references..."):
                try:
                    st.session_state.team_reference_fix_result = fixTeamReferences(int(year))
                    st.rerun()
                except Exception as exc:
                    st.error(f"Fix team references failed: {exc}")

    fix_result = st.session_state.team_reference_fix_result
    if fix_result:
        st.info(
            " | ".join(
                [
                    f"Matched: {fix_result['matched']}",
                    f"Skipped existing: {fix_result['skipped_existing']}",
                    f"Unmatched: {fix_result['unmatched']}",
                    f"Ambiguous: {fix_result['ambiguous']}",
                ]
            )
        )

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

    with c3:
        if st.button("Save Team Reference Changes", key="admin_save_team_refs"):
            try:
                updateTeamReferences(edited_df.to_dict(orient="records"))
                st.success("Team references saved.")
            except Exception as exc:
                st.error(f"Save failed: {exc}")

    if fix_result and fix_result.get("unmatched_rows"):
        st.markdown("**Unmatched Teams**")
        unmatched_df = pd.DataFrame(fix_result["unmatched_rows"])
        st.dataframe(unmatched_df[[c for c in ["TeamID", "KenPomName", "EspnID", "EspnName"] if c in unmatched_df.columns]], use_container_width=True, hide_index=True)

    if fix_result and fix_result.get("ambiguous_rows"):
        st.markdown("**Ambiguous Teams**")
        ambiguous_df = pd.DataFrame(fix_result["ambiguous_rows"])
        st.dataframe(ambiguous_df, use_container_width=True, hide_index=True)


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
