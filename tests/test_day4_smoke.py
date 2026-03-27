"""Smoke tests for Day4 — 5-digit enforcement and compliance metric."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import (
    _is_5digit,
    format_answer,
    format_summary,
    run_batch,
    run_one,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# _is_5digit() helper
# ---------------------------------------------------------------------------

def test_is_5digit_valid():
    assert _is_5digit("00031") is True
    assert _is_5digit("00000") is True
    assert _is_5digit("99999") is True


def test_is_5digit_wrong_length():
    assert _is_5digit("031") is False
    assert _is_5digit("000031") is False


def test_is_5digit_non_numeric():
    assert _is_5digit("0003x") is False
    assert _is_5digit("") is False


def test_is_5digit_non_string():
    assert _is_5digit(31) is False
    assert _is_5digit(None) is False


# ---------------------------------------------------------------------------
# run_one() — 5-digit guarantee on both predicted and expected
# ---------------------------------------------------------------------------

def test_run_one_predicted_always_5digit():
    records = load_jsonl(DATA_PATH)
    for rec in records:
        result = run_one(rec)
        assert _is_5digit(result["predicted"]), (
            f"{rec['id']}: predicted not 5-digit: {result['predicted']!r}"
        )


def test_run_one_expected_always_5digit():
    records = load_jsonl(DATA_PATH)
    for rec in records:
        result = run_one(rec)
        assert _is_5digit(result["expected"]), (
            f"{rec['id']}: expected not 5-digit: {result['expected']!r}"
        )


def test_run_one_normalises_non_padded_answer(tmp_path):
    """run_one() normalises an answer like '31' to '00031'."""
    import json
    f = tmp_path / "test.jsonl"
    record = {
        "id": "test_001", "answer": "31", "domain": "algebra",
        "difficulty": 1, "answer_raw": 31, "answer_transform": "zero_pad_5",
        "contamination_checked": True, "contamination_risk": "low",
        "notes": "", "shadow_eval_version": "v1.0",
    }
    f.write_text(json.dumps(record) + "\n")
    records = load_jsonl(str(f))
    result = run_one(records[0])
    assert result["expected"] == "00031"
    assert _is_5digit(result["expected"])


def test_run_one_raises_on_non_numeric_answer(tmp_path):
    """run_one() raises ValueError for a non-numeric answer."""
    import json
    f = tmp_path / "bad.jsonl"
    record = {
        "id": "bad_001", "answer": "ABCDE", "domain": "algebra",
        "difficulty": 1, "answer_raw": 0, "answer_transform": "zero_pad_5",
        "contamination_checked": True, "contamination_risk": "low",
        "notes": "", "shadow_eval_version": "v1.0",
    }
    f.write_text(json.dumps(record) + "\n")
    records = load_jsonl(str(f))
    with pytest.raises(ValueError):
        run_one(records[0])


# ---------------------------------------------------------------------------
# format_summary() — answer_5digit_compliance metric
# ---------------------------------------------------------------------------

def test_summary_has_compliance_key():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert "answer_5digit_compliance" in summary


def test_compliance_has_required_subkeys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    comp = format_summary(batch)["answer_5digit_compliance"]
    for k in ("compliant", "total", "rate"):
        assert k in comp


def test_compliance_rate_is_1_for_placeholder():
    """Placeholder solver + valid dataset → 100 % compliance."""
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    comp = format_summary(batch)["answer_5digit_compliance"]
    assert comp["compliant"] == comp["total"]
    assert abs(comp["rate"] - 1.0) < 1e-9


def test_compliance_total_matches_batch_total():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert summary["answer_5digit_compliance"]["total"] == summary["total"]


def test_compliance_detects_non_5digit_predicted():
    """A stub result with a bad predicted value lowers compliance."""
    stub_results = [
        {"id": "x1", "correct": False, "predicted": "031",   "expected": "00031"},
        {"id": "x2", "correct": False, "predicted": "00000", "expected": "00063"},
    ]
    stub_batch = {"results": stub_results, "total": 2, "correct": 0, "accuracy": 0.0}
    comp = format_summary(stub_batch)["answer_5digit_compliance"]
    assert comp["compliant"] == 1
    assert comp["total"] == 2
    assert abs(comp["rate"] - 0.5) < 1e-9


def test_compliance_with_limit():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=5)
    comp = format_summary(batch)["answer_5digit_compliance"]
    assert comp["total"] == 5
    assert comp["compliant"] == 5


# ---------------------------------------------------------------------------
# format_answer() — normalisation edge cases (Day4 context)
# ---------------------------------------------------------------------------

def test_format_answer_already_5digits():
    assert format_answer("00031") == "00031"


def test_format_answer_integer_string():
    assert format_answer("31") == "00031"


def test_format_answer_large_number():
    assert format_answer("10000") == "10000"


def test_format_answer_negative_raises():
    with pytest.raises(ValueError, match="non-negative"):
        format_answer("-1")
