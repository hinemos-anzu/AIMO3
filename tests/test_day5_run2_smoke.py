"""Smoke tests for Day5 Run2 — Execution Retry logic."""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import (
    ExecTimeoutError,
    format_summary,
    run_batch_with_retry,
    run_one_with_retry,
    solve_placeholder,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# run_one_with_retry() — argument validation
# ---------------------------------------------------------------------------

def test_max_retries_negative_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="max_retries"):
        run_one_with_retry(records[0], max_retries=-1)


def test_timeout_sec_zero_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="timeout_sec"):
        run_one_with_retry(records[0], timeout_sec=0)


def test_timeout_sec_negative_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="timeout_sec"):
        run_one_with_retry(records[0], timeout_sec=-1.0)


# ---------------------------------------------------------------------------
# run_one_with_retry() — output shape with placeholder (no errors)
# ---------------------------------------------------------------------------

def test_result_has_retry_keys():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0])
    for key in ("id", "domain", "difficulty", "predicted", "expected",
                "correct", "retries_used", "exec_error_count",
                "elapsed_sec", "exec_errors"):
        assert key in result, f"Missing key: {key}"


def test_no_retry_needed_retries_used_zero():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0], max_retries=2)
    assert result["retries_used"] == 0  # placeholder never fails


def test_no_retry_needed_exec_error_count_zero():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0], max_retries=2)
    assert result["exec_error_count"] == 0


def test_exec_errors_is_empty_list_on_success():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0])
    assert result["exec_errors"] == []


def test_elapsed_sec_is_non_negative_float():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0])
    assert isinstance(result["elapsed_sec"], float)
    assert result["elapsed_sec"] >= 0.0


def test_predicted_is_5digit():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0])
    assert len(result["predicted"]) == 5
    assert result["predicted"].isdigit()


def test_expected_is_5digit():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0])
    assert len(result["expected"]) == 5
    assert result["expected"].isdigit()


# ---------------------------------------------------------------------------
# run_one_with_retry() — retry fires on solver exceptions (monkeypatch)
# ---------------------------------------------------------------------------

def test_retry_fires_on_runtime_error(monkeypatch):
    """Solver fails once then succeeds — retries_used == 1."""
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def flaky_solver(record):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated execution failure")
        return "00042"

    monkeypatch.setattr(
        "day1_minimal_baseline.pipeline.solve_placeholder", flaky_solver
    )
    result = run_one_with_retry(records[0], max_retries=2)
    assert result["retries_used"] == 1
    assert result["exec_error_count"] == 1
    assert result["predicted"] == "00042"
    assert len(result["exec_errors"]) == 1


def test_retry_exhausted_raises(monkeypatch):
    """Solver always fails — RuntimeError after max_retries+1 attempts."""
    records = load_jsonl(DATA_PATH)

    def always_fail(record):
        raise RuntimeError("always fails")

    monkeypatch.setattr(
        "day1_minimal_baseline.pipeline.solve_placeholder", always_fail
    )
    with pytest.raises(RuntimeError, match="all .* attempt"):
        run_one_with_retry(records[0], max_retries=1)


def test_same_error_not_retried_infinitely(monkeypatch):
    """Max_retries=2 → exactly 3 calls total, then raises."""
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def counting_fail(record):
        call_count["n"] += 1
        raise ValueError("always bad")

    monkeypatch.setattr(
        "day1_minimal_baseline.pipeline.solve_placeholder", counting_fail
    )
    with pytest.raises(RuntimeError):
        run_one_with_retry(records[0], max_retries=2)
    assert call_count["n"] == 3  # 1 original + 2 retries


def test_timeout_error_not_retried(monkeypatch):
    """ExecTimeoutError propagates immediately — no retry."""
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def slow_solver(record):
        call_count["n"] += 1
        raise ExecTimeoutError("timeout")

    monkeypatch.setattr(
        "day1_minimal_baseline.pipeline.solve_placeholder", slow_solver
    )
    with pytest.raises(ExecTimeoutError):
        run_one_with_retry(records[0], max_retries=5)
    assert call_count["n"] == 1  # timeout is never retried


# ---------------------------------------------------------------------------
# run_batch_with_retry() — shape and stats
# ---------------------------------------------------------------------------

def test_batch_retry_has_extra_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=3)
    for key in ("retry_count_used", "exec_error_count",
                "avg_runtime_sec", "max_runtime_sec",
                "max_retries_setting", "timeout_sec_setting"):
        assert key in batch, f"Missing key: {key}"


def test_batch_retry_zero_retries_used_for_placeholder():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, max_retries=2)
    assert batch["retry_count_used"] == 0
    assert batch["exec_error_count"] == 0


def test_batch_retry_max_runtime_below_timeout():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=5, timeout_sec=250.0)
    assert batch["max_runtime_sec"] < 250.0


def test_batch_retry_avg_runtime_non_negative():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=5)
    assert batch["avg_runtime_sec"] >= 0.0


def test_batch_retry_settings_recorded():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=3, max_retries=1, timeout_sec=100.0)
    assert batch["max_retries_setting"] == 1
    assert batch["timeout_sec_setting"] == 100.0


def test_batch_retry_limit_invalid():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="limit"):
        run_batch_with_retry(records, limit=0)


# ---------------------------------------------------------------------------
# format_summary() — retry_stats conditional key
# ---------------------------------------------------------------------------

def test_format_summary_includes_retry_stats_when_present():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=3, max_retries=1)
    summary = format_summary(batch)
    assert "retry_stats" in summary


def test_format_summary_no_retry_stats_without_retry_batch():
    records = load_jsonl(DATA_PATH)
    from day1_minimal_baseline.pipeline import run_batch
    batch = run_batch(records, limit=3)
    summary = format_summary(batch)
    assert "retry_stats" not in summary


def test_retry_stats_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=3, max_retries=1)
    rs = format_summary(batch)["retry_stats"]
    for key in ("retry_count_used", "exec_error_count",
                "avg_runtime_sec", "max_runtime_sec",
                "max_retries_setting", "timeout_sec_setting"):
        assert key in rs


def test_retry_stats_zero_for_placeholder():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, max_retries=2)
    rs = format_summary(batch)["retry_stats"]
    assert rs["retry_count_used"] == 0
    assert rs["exec_error_count"] == 0
    assert rs["max_retries_setting"] == 2
