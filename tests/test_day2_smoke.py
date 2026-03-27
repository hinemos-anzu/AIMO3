"""Smoke tests for Day2 batch pipeline."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import run_batch

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# run_batch() — shape and type checks
# ---------------------------------------------------------------------------

def test_run_batch_all_returns_summary_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    for key in ("results", "total", "correct", "accuracy"):
        assert key in batch


def test_run_batch_total_matches_dataset():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    assert batch["total"] == len(records)


def test_run_batch_results_length_matches_total():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    assert len(batch["results"]) == batch["total"]


def test_run_batch_limit_3():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=3)
    assert batch["total"] == 3
    assert len(batch["results"]) == 3


def test_run_batch_limit_1():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=1)
    assert batch["total"] == 1
    assert batch["results"][0]["id"] == records[0]["id"]


def test_run_batch_limit_equals_dataset_size():
    records = load_jsonl(DATA_PATH)
    batch_all = run_batch(records)
    batch_lim = run_batch(records, limit=len(records))
    assert batch_lim["total"] == batch_all["total"]


def test_run_batch_limit_larger_than_dataset():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=9999)
    assert batch["total"] == len(records)


# ---------------------------------------------------------------------------
# run_batch() — accuracy and correct count
# ---------------------------------------------------------------------------

def test_run_batch_correct_is_int():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    assert isinstance(batch["correct"], int)


def test_run_batch_accuracy_is_float():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    assert isinstance(batch["accuracy"], float)


def test_run_batch_accuracy_range():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    assert 0.0 <= batch["accuracy"] <= 1.0


def test_run_batch_accuracy_consistent_with_correct():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    expected_acc = batch["correct"] / batch["total"]
    assert abs(batch["accuracy"] - expected_acc) < 1e-9


def test_run_batch_placeholder_correct_is_zero():
    # placeholder always returns "00000"; dataset answers are never "00000"
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    assert batch["correct"] == 0


def test_run_batch_order_preserved():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=5)
    for i, result in enumerate(batch["results"]):
        assert result["id"] == records[i]["id"]


# ---------------------------------------------------------------------------
# run_batch() — error cases
# ---------------------------------------------------------------------------

def test_run_batch_limit_zero_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="limit must be"):
        run_batch(records, limit=0)


def test_run_batch_limit_negative_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="limit must be"):
        run_batch(records, limit=-1)
