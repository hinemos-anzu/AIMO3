"""Smoke tests for Day5 Run3 — Candidate count (N) scaling."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import (
    ExecTimeoutError,
    format_summary,
    generate_candidates,
    run_batch_with_candidates,
    run_one_with_candidates,
    select_by_majority,
    solve_placeholder,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# generate_candidates()
# ---------------------------------------------------------------------------

def test_generate_candidates_correct_count():
    records = load_jsonl(DATA_PATH)
    for n in (1, 4, 16):
        cands = generate_candidates(records[0], n)
        assert len(cands) == n, f"Expected {n} candidates, got {len(cands)}"


def test_generate_candidates_all_5digit():
    records = load_jsonl(DATA_PATH)
    for n in (1, 8):
        cands = generate_candidates(records[0], n)
        for c in cands:
            assert len(c) == 5 and c.isdigit(), f"Not 5-digit: {c!r}"


def test_generate_candidates_placeholder_all_same():
    records = load_jsonl(DATA_PATH)
    cands = generate_candidates(records[0], 16)
    assert all(c == "00000" for c in cands)


def test_generate_candidates_zero_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="num_candidates"):
        generate_candidates(records[0], 0)


def test_generate_candidates_negative_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="num_candidates"):
        generate_candidates(records[0], -1)


# ---------------------------------------------------------------------------
# select_by_majority()
# ---------------------------------------------------------------------------

def test_select_majority_single():
    assert select_by_majority(["00031"]) == "00031"


def test_select_majority_clear_winner():
    assert select_by_majority(["00031", "00031", "00063"]) == "00031"


def test_select_majority_tie_lexicographic():
    # tie between "00031" and "00063" → smaller wins
    assert select_by_majority(["00031", "00063"]) == "00031"


def test_select_majority_all_same():
    assert select_by_majority(["00000"] * 16) == "00000"


def test_select_majority_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        select_by_majority([])


# ---------------------------------------------------------------------------
# run_one_with_candidates() — output shape
# ---------------------------------------------------------------------------

def test_run_one_candidates_result_keys():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_candidates(records[0], num_candidates=4)
    for key in ("id", "domain", "difficulty", "predicted", "expected", "correct",
                "retries_used", "exec_error_count", "elapsed_sec", "exec_errors",
                "num_candidates_setting", "candidate_diversity", "candidates"):
        assert key in result, f"Missing key: {key}"


def test_run_one_candidates_count_recorded():
    records = load_jsonl(DATA_PATH)
    for n in (1, 4, 8):
        result = run_one_with_candidates(records[0], num_candidates=n)
        assert result["num_candidates_setting"] == n
        assert len(result["candidates"]) == n


def test_run_one_candidates_predicted_5digit():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_candidates(records[0], num_candidates=8)
    assert len(result["predicted"]) == 5
    assert result["predicted"].isdigit()


def test_run_one_candidates_diversity_range():
    records = load_jsonl(DATA_PATH)
    result = run_one_with_candidates(records[0], num_candidates=16)
    assert 0.0 <= result["candidate_diversity"] <= 1.0


def test_run_one_candidates_placeholder_diversity_is_min():
    """Placeholder returns identical candidates → diversity = 1/N."""
    records = load_jsonl(DATA_PATH)
    result = run_one_with_candidates(records[0], num_candidates=16)
    # all "00000" → unique=1 → diversity = 1/16
    assert abs(result["candidate_diversity"] - 1 / 16) < 1e-6


def test_run_one_candidates_n1_equivalent_to_retry():
    """N=1 should give same predicted as run_one_with_retry()."""
    from day1_minimal_baseline.pipeline import run_one_with_retry
    records = load_jsonl(DATA_PATH)
    r_cand = run_one_with_candidates(records[0], num_candidates=1)
    r_retry = run_one_with_retry(records[0])
    assert r_cand["predicted"] == r_retry["predicted"]
    assert r_cand["expected"] == r_retry["expected"]


# ---------------------------------------------------------------------------
# run_one_with_candidates() — argument validation
# ---------------------------------------------------------------------------

def test_num_candidates_zero_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="num_candidates"):
        run_one_with_candidates(records[0], num_candidates=0)


def test_max_retries_negative_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="max_retries"):
        run_one_with_candidates(records[0], num_candidates=4, max_retries=-1)


def test_timeout_sec_zero_raises():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="timeout_sec"):
        run_one_with_candidates(records[0], num_candidates=4, timeout_sec=0)


# ---------------------------------------------------------------------------
# run_one_with_candidates() — OOM and timeout not retried (monkeypatch)
# ---------------------------------------------------------------------------

def test_memory_error_not_retried(monkeypatch):
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def oom_solver(record):
        call_count["n"] += 1
        raise MemoryError("simulated OOM")

    monkeypatch.setattr("day1_minimal_baseline.pipeline.solve_placeholder", oom_solver)
    with pytest.raises(MemoryError):
        run_one_with_candidates(records[0], num_candidates=4, max_retries=5)
    assert call_count["n"] == 1  # OOM never retried


def test_timeout_not_retried(monkeypatch):
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def timeout_solver(record):
        call_count["n"] += 1
        raise ExecTimeoutError("timeout")

    monkeypatch.setattr("day1_minimal_baseline.pipeline.solve_placeholder", timeout_solver)
    with pytest.raises(ExecTimeoutError):
        run_one_with_candidates(records[0], num_candidates=4, max_retries=5)
    assert call_count["n"] == 1  # timeout never retried


def test_runtime_error_retried(monkeypatch):
    records = load_jsonl(DATA_PATH)
    call_count = {"n": 0}

    def flaky_solver(record):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("first call fails")
        return "00042"

    monkeypatch.setattr("day1_minimal_baseline.pipeline.solve_placeholder", flaky_solver)
    result = run_one_with_candidates(records[0], num_candidates=1, max_retries=1)
    assert result["retries_used"] == 1
    assert result["predicted"] == "00042"


# ---------------------------------------------------------------------------
# run_batch_with_candidates() — shape and stats
# ---------------------------------------------------------------------------

def test_batch_candidates_has_candidate_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=3, num_candidates=4)
    for key in ("num_candidates_setting", "avg_candidate_diversity"):
        assert key in batch, f"Missing key: {key}"


def test_batch_candidates_setting_recorded():
    records = load_jsonl(DATA_PATH)
    for n in (1, 4, 8):
        batch = run_batch_with_candidates(records, limit=3, num_candidates=n)
        assert batch["num_candidates_setting"] == n


def test_batch_candidates_diversity_range():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=5, num_candidates=8)
    assert 0.0 <= batch["avg_candidate_diversity"] <= 1.0


def test_batch_candidates_n1_accuracy_equals_run_batch():
    """N=1 should give same accuracy as run_batch()."""
    from day1_minimal_baseline.pipeline import run_batch
    records = load_jsonl(DATA_PATH)
    b_orig = run_batch(records)
    b_cand = run_batch_with_candidates(records, num_candidates=1)
    assert b_cand["accuracy"] == b_orig["accuracy"]


def test_batch_candidates_limit_invalid():
    records = load_jsonl(DATA_PATH)
    with pytest.raises(ValueError, match="limit"):
        run_batch_with_candidates(records, limit=0, num_candidates=4)


# ---------------------------------------------------------------------------
# format_summary() — candidate_stats conditional key
# ---------------------------------------------------------------------------

def test_format_summary_has_candidate_stats():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=3, num_candidates=4)
    summary = format_summary(batch)
    assert "candidate_stats" in summary


def test_format_summary_no_candidate_stats_for_run_batch():
    from day1_minimal_baseline.pipeline import run_batch
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=3)
    summary = format_summary(batch)
    assert "candidate_stats" not in summary


def test_candidate_stats_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch_with_candidates(records, limit=3, num_candidates=4)
    cs = format_summary(batch)["candidate_stats"]
    assert "num_candidates_setting" in cs
    assert "avg_candidate_diversity" in cs


def test_candidate_stats_n_values_16_32():
    """Smoke test with N=16 and N=32 on a small subset."""
    records = load_jsonl(DATA_PATH)
    for n in (16, 32):
        batch = run_batch_with_candidates(records, limit=2, num_candidates=n)
        cs = format_summary(batch)["candidate_stats"]
        assert cs["num_candidates_setting"] == n
        # placeholder: all identical → diversity = 1/n
        expected_div = round(1 / n, 6)
        assert abs(cs["avg_candidate_diversity"] - expected_div) < 1e-5, (
            f"N={n}: expected avg_diversity≈{expected_div}, "
            f"got {cs['avg_candidate_diversity']}"
        )
