"""Tests for app_logic/export_brackets.py."""

import io
import json
import zipfile

import pytest

from app_logic.export_brackets import (
    _safe_filename,
    build_brackets_zip,
    export_zip_filename,
)


def test_safe_filename_strips_special_chars() -> None:
    assert _safe_filename("My Bracket! 2026") == "My_Bracket__2026"


def test_safe_filename_allows_hyphen_and_underscore() -> None:
    assert _safe_filename("My-Bracket_2026") == "My-Bracket_2026"


def test_safe_filename_truncates_long_names() -> None:
    assert len(_safe_filename("x" * 100)) <= 64


def test_safe_filename_empty_string() -> None:
    assert _safe_filename("") == ""


def test_build_brackets_zip_single() -> None:
    bracket = {"id": "bracket_abc123", "name": "Test", "champion": "Duke"}
    raw = build_brackets_zip([bracket])
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert len(zf.namelist()) == 1
        assert zf.namelist()[0] == "Test_bracket_abc123.json"
        data = json.loads(zf.read(zf.namelist()[0]))
        assert data["champion"] == "Duke"


def test_build_brackets_zip_multiple() -> None:
    brackets = [
        {"id": "bracket_aaa", "name": "Alpha"},
        {"id": "bracket_bbb", "name": "Beta"},
    ]
    raw = build_brackets_zip(brackets)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        assert len(names) == 2
        assert "Alpha_bracket_aaa.json" in names
        assert "Beta_bracket_bbb.json" in names


def test_build_brackets_zip_preserves_all_fields() -> None:
    bracket = {
        "id": "bracket_xyz",
        "name": "Full",
        "champion": "Kentucky",
        "upset_counts": {"Round of 64": 3},
        "year": 2026,
    }
    raw = build_brackets_zip([bracket])
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        data = json.loads(zf.read(zf.namelist()[0]))
    assert data == bracket


def test_build_brackets_zip_sanitizes_name_in_filename() -> None:
    bracket = {"id": "bracket_001", "name": "My Bracket! 2026"}
    raw = build_brackets_zip([bracket])
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert zf.namelist()[0] == "My_Bracket__2026_bracket_001.json"


def test_build_brackets_zip_empty_list() -> None:
    raw = build_brackets_zip([])
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert zf.namelist() == []


def test_export_zip_filename_format() -> None:
    name = export_zip_filename(3)
    assert name.startswith("brackets_3_")
    assert name.endswith(".zip")


def test_export_zip_filename_count_reflected() -> None:
    assert export_zip_filename(1).startswith("brackets_1_")
    assert export_zip_filename(10).startswith("brackets_10_")
