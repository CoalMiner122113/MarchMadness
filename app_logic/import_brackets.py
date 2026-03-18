"""Bracket import utilities — validation and preparation of bracket JSON files."""

import uuid
from datetime import datetime, timezone

ROUND_NAMES: list[str] = [
    "Round of 64",
    "Round of 32",
    "Sweet 16",
    "Elite 8",
    "Final Four",
    "Championship",
]

GAME_COUNTS: dict[str, int] = {
    "Round of 64": 32,
    "Round of 32": 16,
    "Sweet 16": 8,
    "Elite 8": 4,
    "Final Four": 2,
    "Championship": 1,
}

REQUIRED_GAME_FIELDS: set[str] = {
    "division",
    "team1",
    "team2",
    "winner",
    "loser",
    "winner_espn_probability",
    "winner_kenpom_probability",
    "winner_simulation_probability",
    "winner_moneyline",
}


def validate_bracket(data: dict) -> list[str]:
    """Validate a bracket dict parsed from an imported JSON file.

    Checks structural integrity without requiring optional fields such as
    ``seeding``, ``upset_counts``, ``source``, ``year``, or ``saved_at``.

    Args:
        data: Parsed bracket dict from JSON.

    Returns:
        List of human-readable error strings. An empty list means the
        bracket is valid and safe to import.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["File does not contain a JSON object at the top level."]

    results = data.get("results")
    if results is None:
        errors.append("Missing required field: 'results'.")
        return errors  # can't validate further without results
    if not isinstance(results, dict):
        errors.append("'results' must be a JSON object (dict).")
        return errors

    for round_name in ROUND_NAMES:
        if round_name not in results:
            errors.append(f"Missing round in results: '{round_name}'.")
            continue

        games = results[round_name]
        if not isinstance(games, list):
            errors.append(f"'{round_name}': expected a list of games, got {type(games).__name__}.")
            continue

        expected = GAME_COUNTS[round_name]
        if len(games) != expected:
            errors.append(
                f"'{round_name}': expected {expected} game{'s' if expected != 1 else ''}, "
                f"got {len(games)}."
            )

        for i, game in enumerate(games):
            if not isinstance(game, dict):
                errors.append(f"'{round_name}' game {i}: not a JSON object.")
                continue
            missing = REQUIRED_GAME_FIELDS - game.keys()
            if missing:
                errors.append(
                    f"'{round_name}' game {i}: missing field(s): "
                    f"{', '.join(sorted(missing))}."
                )
                continue
            if game["winner"] not in (game["team1"], game["team2"]):
                errors.append(
                    f"'{round_name}' game {i}: 'winner' ('{game['winner']}') "
                    f"is not 'team1' or 'team2'."
                )

    # Cross-check champion vs Championship result (soft warning only)
    champion = data.get("champion")
    championship_games = results.get("Championship", [])
    if champion and championship_games and isinstance(championship_games[0], dict):
        actual_winner = championship_games[0].get("winner")
        if actual_winner and actual_winner != champion:
            errors.append(
                f"'champion' field ('{champion}') does not match the "
                f"Championship game winner ('{actual_winner}')."
            )

    return errors


def _deduplicate_name(name: str, existing_names: list[str]) -> str:
    """Return a unique bracket name by appending (1), (2), … if needed.

    Args:
        name: Desired bracket name.
        existing_names: Names already in use in the current session.

    Returns:
        A name that is not in ``existing_names``.
    """
    if name not in existing_names:
        return name
    counter = 1
    while f"{name} ({counter})" in existing_names:
        counter += 1
    return f"{name} ({counter})"


def prepare_bracket(data: dict, filename: str, existing_names: list[str]) -> dict:
    """Build a final bracket dict ready to append to the session payload.

    The bracket's ``name`` is derived from ``filename`` (with ``.json``
    stripped) and de-duplicated against ``existing_names``.  A fresh
    ``id`` is always generated so imported brackets never collide with
    existing ones.

    Args:
        data: Validated bracket dict parsed from the uploaded JSON file.
        filename: Original uploaded filename (e.g. ``"My_Bracket.json"``).
        existing_names: Names already used in the current session.

    Returns:
        A complete bracket dict safe to append to ``payload["saved_brackets"]``.
    """
    raw_name = filename.removesuffix(".json")
    name = _deduplicate_name(raw_name, existing_names)

    new_id = f"bracket_{uuid.uuid4().hex[:10]}"

    # Derive champion from Championship result if not present in data
    champion = data.get("champion", "")
    if not champion:
        championship = data.get("results", {}).get("Championship", [])
        if championship and isinstance(championship[0], dict):
            champion = championship[0].get("winner", "")

    return {
        "id": new_id,
        "name": name,
        "saved_at": data.get(
            "saved_at",
            datetime.now(tz=timezone.utc).isoformat(),
        ),
        "year": data.get("year", datetime.now().year),
        "source": data.get("source", "imported"),
        "default_probability_source": data.get("default_probability_source", ""),
        "champion": champion,
        "results": data["results"],
        "upset_counts": data.get("upset_counts", {}),
        "seeding": data.get("seeding", []),
    }
