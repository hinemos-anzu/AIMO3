"""Smoke tests for Day1 minimal baseline."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import format_answer, run_one, solve_placeholder

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# io.py
# ---------------------------------------------------------------------------

def test_load_jsonl_returns_records():
    records = load_jsonl(DATA_PATH)
    assert len(records) > 0


def test_load_jsonl_required_fields():
    records = load_jsonl(DATA_PATH)
    for rec in records:
        for field in ("id", "answer", "domain", "difficulty"):
            assert field in rec, f"Missing field {field!r} in {rec['id']}"


def test_load_jsonl_answer_is_5digits():
    records = load_jsonl(DATA_PATH)
    for rec in records:
        assert len(rec["answer"]) == 5, f"{rec['id']}: answer not 5 chars: {rec['answer']!r}"
        assert rec["answer"].isdigit(), f"{rec['id']}: answer not numeric: {rec['answer']!r}"


def test_load_jsonl_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_jsonl("/nonexistent/path/shadow_eval.jsonl")


def test_load_jsonl_empty_file(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_jsonl(str(f))


def test_load_jsonl_bad_json(tmp_path):
    f = tmp_path / "bad.jsonl"
    f.write_text("{not valid json}\n")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_jsonl(str(f))


def test_load_jsonl_missing_field(tmp_path):
    f = tmp_path / "missing.jsonl"
    f.write_text('{"id": "x", "domain": "algebra"}\n')  # missing answer, difficulty
    with pytest.raises(ValueError, match="missing required fields"):
        load_jsonl(str(f))


# ---------------------------------------------------------------------------
# pipeline.py
# ---------------------------------------------------------------------------

def test_solve_placeholder_returns_5digits():
    records = load_jsonl(DATA_PATH)
    result = solve_placeholder(records[0])
    assert result == "00000"
    assert len(result) == 5


def test_format_answer_zero_pad():
    assert format_answer("31") == "00031"
    assert format_answer("0") == "00000"
    assert format_answer("12345") == "12345"


def test_format_answer_invalid():
    with pytest.raises(ValueError):
        format_answer("abc")


def test_run_one_output_shape():
    records = load_jsonl(DATA_PATH)
    result = run_one(records[0])
    for key in ("id", "domain", "difficulty", "predicted", "expected", "correct"):
        assert key in result


def test_run_one_predicted_is_5digits():
    records = load_jsonl(DATA_PATH)
    result = run_one(records[0])
    assert len(result["predicted"]) == 5
    assert result["predicted"].isdigit()
