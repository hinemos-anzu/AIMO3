"""Smoke tests for Day6 — solver adapter and injection."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import (
    format_summary,
    generate_candidates,
    run_batch_with_candidates,
    run_batch_with_retry,
    run_one_with_candidates,
    run_one_with_retry,
)
from day1_minimal_baseline.solver import (
    LLM,
    PLACEHOLDER,
    SolverConfigError,
    create_solver,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# create_solver() — mode validation
# ---------------------------------------------------------------------------

def test_create_solver_placeholder_returns_callable():
    solver = create_solver(PLACEHOLDER)
    assert callable(solver)


def test_create_solver_placeholder_returns_zeros():
    records = load_jsonl(DATA_PATH)
    solver = create_solver(PLACEHOLDER)
    assert solver(records[0]) == "00000"


def test_create_solver_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown solver mode"):
        create_solver("does_not_exist")


def test_create_solver_llm_raises_without_api_key(monkeypatch):
    """LLM mode without ANTHROPIC_API_KEY must raise SolverConfigError."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SolverConfigError, match="ANTHROPIC_API_KEY"):
        create_solver(LLM)


def test_solver_config_error_is_value_error():
    assert issubclass(SolverConfigError, ValueError)


def test_placeholder_constant_value():
    assert PLACEHOLDER == "placeholder"


def test_llm_constant_value():
    assert LLM == "llm"


# ---------------------------------------------------------------------------
# solver injection into generate_candidates()
# ---------------------------------------------------------------------------

def test_generate_candidates_custom_solver():
    records = load_jsonl(DATA_PATH)
    solver = create_solver(PLACEHOLDER)
    cands = generate_candidates(records[0], 4, solver=solver)
    assert len(cands) == 4
    assert all(c == "00000" for c in cands)


def test_generate_candidates_injected_deterministic_solver():
    """Injected solver returning '42' should be normalised to '00042'."""
    records = load_jsonl(DATA_PATH)

    def always_42(record):
        return "42"

    cands = generate_candidates(records[0], 3, solver=always_42)
    assert cands == ["00042", "00042", "00042"]


def test_generate_candidates_injected_varied_solver():
    """Injected solver returning different values per call."""
    records = load_jsonl(DATA_PATH)
    answers = ["31", "63", "57"]
    call_count = {"n": 0}

    def cycling_solver(record):
        val = answers[call_count["n"] % len(answers)]
        call_count["n"] += 1
        return val

    cands = generate_candidates(records[0], 3, solver=cycling_solver)
    assert cands == ["00031", "00063", "00057"]


# ---------------------------------------------------------------------------
# solver injection into run_one_with_retry()
# ---------------------------------------------------------------------------

def test_run_one_with_retry_custom_solver():
    records = load_jsonl(DATA_PATH)
    expected_answer = records[0]["answer"]  # e.g. "00031"

    def correct_solver(record):
        return record["answer"]  # returns the gold answer

    result = run_one_with_retry(records[0], solver=correct_solver)
    assert result["correct"] is True
    assert result["predicted"] == expected_answer


def test_run_one_with_retry_parse_failure_counted(monkeypatch):
    """Solver returning non-numeric causes parse failure, then retry succeeds."""
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def first_call_bad(record):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "not_a_number"  # will cause ValueError in format_answer
        return "00031"

    result = run_one_with_retry(records[0], max_retries=1, solver=first_call_bad)
    assert result["parse_failure_count"] == 1
    assert result["exec_error_count"] == 1
    assert result["retries_used"] == 1
    assert result["predicted"] == "00031"


def test_run_one_with_retry_parse_failure_key_present_on_success():
    """parse_failure_count is present even when solver succeeds first try."""
    records = load_jsonl(DATA_PATH)
    result = run_one_with_retry(records[0])
    assert "parse_failure_count" in result
    assert result["parse_failure_count"] == 0


# ---------------------------------------------------------------------------
# solver injection into run_one_with_candidates()
# ---------------------------------------------------------------------------

def test_run_one_with_candidates_correct_solver():
    records = load_jsonl(DATA_PATH)
    expected_answer = records[0]["answer"]

    def correct_solver(record):
        return record["answer"]

    result = run_one_with_candidates(records[0], num_candidates=4, solver=correct_solver)
    assert result["correct"] is True
    assert result["predicted"] == expected_answer


def test_run_one_with_candidates_majority_wins():
    """3 out of 4 candidates correct → majority selects correct answer."""
    records = load_jsonl(DATA_PATH)
    gold = records[0]["answer"]   # "00031"
    call_count = {"n": 0}

    def mostly_correct(record):
        call_count["n"] += 1
        return gold if call_count["n"] <= 3 else "00063"  # 3 correct, 1 wrong

    result = run_one_with_candidates(records[0], num_candidates=4, solver=mostly_correct)
    assert result["correct"] is True
    assert result["candidate_diversity"] > 0  # at least 2 distinct values


def test_run_one_with_candidates_parse_failure_key_present():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_candidates(records[0], num_candidates=2)
    assert "parse_failure_count" in result


# ---------------------------------------------------------------------------
# solver injection into run_batch_with_candidates()
# ---------------------------------------------------------------------------

def test_run_batch_with_candidates_custom_solver_non_zero_accuracy():
    """Injected solver returning gold answer → accuracy should be 1.0."""
    records = load_jsonl(DATA_PATH)

    def oracle_solver(record):
        return record["answer"]

    batch = run_batch_with_candidates(records, limit=5, num_candidates=1,
                                      solver=oracle_solver)
    assert batch["accuracy"] == 1.0
    assert batch["correct"] == 5


def test_run_batch_with_candidates_parse_failure_in_batch():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=3, num_candidates=1)
    assert "parse_failure_count" in batch
    assert batch["parse_failure_count"] == 0  # placeholder never parses wrong


def test_run_batch_with_retry_solver_injection():
    records = load_jsonl(DATA_PATH)

    def oracle_solver(record):
        return record["answer"]

    batch = run_batch_with_retry(records, limit=3, solver=oracle_solver)
    assert batch["accuracy"] == 1.0


# ---------------------------------------------------------------------------
# format_summary() — parse_stats
# ---------------------------------------------------------------------------

def test_format_summary_has_parse_stats_from_candidates_batch():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=3, num_candidates=1)
    summary = format_summary(batch)
    assert "parse_stats" in summary


def test_format_summary_parse_stats_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=3)
    ps = format_summary(batch)["parse_stats"]
    assert "parse_success_count" in ps
    assert "parse_failure_count" in ps


def test_format_summary_no_parse_stats_for_plain_run_batch():
    from day1_minimal_baseline.pipeline import run_batch
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=3)
    summary = format_summary(batch)
    assert "parse_stats" not in summary


def test_format_summary_parse_stats_from_retry_batch():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_retry(records, limit=3, max_retries=1)
    summary = format_summary(batch)
    assert "parse_stats" in summary
