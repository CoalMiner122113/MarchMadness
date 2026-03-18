"""Bracket export utilities — build in-memory zip archives for download."""

import io
import json
import re
import zipfile
from datetime import datetime


def _safe_filename(name: str) -> str:
    """Sanitize a bracket name for use as a filesystem-safe filename.

    Args:
        name: Raw bracket name string.

    Returns:
        Alphanumeric/underscore/hyphen string truncated to 64 characters.
    """
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)[:64]


def build_brackets_zip(brackets: list[dict]) -> bytes:
    """Pack a list of bracket dicts into an in-memory zip of JSON files.

    Each bracket is stored as a single file named::

        {safe_name}_{bracket_id}.json

    The zip is designed to be re-imported: each file is a standalone
    bracket snapshot with all fields intact (id, name, saved_at, year,
    source, champion, results, upset_counts, seeding).

    Args:
        brackets: List of bracket dicts as stored in the session payload.

    Returns:
        Raw zip bytes suitable for ``st.download_button``.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for bracket in brackets:
            safe_name = _safe_filename(bracket.get("name", "bracket"))
            bid = bracket.get("id", "unknown")
            filename = f"{safe_name}_{bid}.json"
            zf.writestr(filename, json.dumps(bracket, indent=2))
    return buf.getvalue()


def export_zip_filename(count: int) -> str:
    """Generate a timestamped default filename for the exported zip.

    Args:
        count: Number of brackets being exported.

    Returns:
        Filename string, e.g. ``'brackets_3_20260317_142301.zip'``.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"brackets_{count}_{ts}.zip"
