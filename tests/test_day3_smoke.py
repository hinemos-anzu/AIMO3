"""Smoke tests for Day3 format_summary() and breakdown."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import format_summary, run_batch

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


# ---------------------------------------------------------------------------
# format_summary() — always-present keys
# ---------------------------------------------------------------------------

def test_summary_has_required_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    for key in ("total", "correct", "accuracy"):
        assert key in summary


def test_summary_total_matches_batch():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert summary["total"] == batch["total"]


def test_summary_correct_matches_batch():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert summary["correct"] == batch["correct"]


def test_summary_accuracy_matches_batch():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert abs(summary["accuracy"] - batch["accuracy"]) < 1e-9


# ---------------------------------------------------------------------------
# format_summary() — domain breakdown (dataset has domain field)
# ---------------------------------------------------------------------------

def test_summary_has_domain_breakdown():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert "breakdown_domain" in summary


def test_domain_breakdown_expected_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    bd = summary["breakdown_domain"]
    for domain in ("algebra", "combinatorics", "geometry", "number_theory"):
        assert domain in bd, f"Missing domain: {domain}"


def test_domain_breakdown_entry_keys():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    bd = format_summary(batch)["breakdown_domain"]
    for domain, stats in bd.items():
        for k in ("total", "correct", "accuracy"):
            assert k in stats, f"Missing key {k!r} in domain {domain!r}"


def test_domain_breakdown_totals_sum_to_overall():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    bd_total = sum(s["total"] for s in summary["breakdown_domain"].values())
    assert bd_total == summary["total"]


def test_domain_breakdown_corrects_sum_to_overall():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    bd_correct = sum(s["correct"] for s in summary["breakdown_domain"].values())
    assert bd_correct == summary["correct"]


def test_domain_breakdown_accuracy_consistent():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    bd = format_summary(batch)["breakdown_domain"]
    for domain, stats in bd.items():
        expected = stats["correct"] / stats["total"]
        assert abs(stats["accuracy"] - expected) < 1e-9, f"Accuracy mismatch for {domain}"


# ---------------------------------------------------------------------------
# format_summary() — difficulty breakdown (dataset has difficulty field)
# ---------------------------------------------------------------------------

def test_summary_has_difficulty_breakdown():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    assert "breakdown_difficulty" in summary


def test_difficulty_breakdown_expected_levels():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    bd = format_summary(batch)["breakdown_difficulty"]
    assert 1 in bd
    assert 2 in bd


def test_difficulty_breakdown_totals_sum_to_overall():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    bd_total = sum(s["total"] for s in summary["breakdown_difficulty"].values())
    assert bd_total == summary["total"]


def test_difficulty_breakdown_corrects_sum_to_overall():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records)
    summary = format_summary(batch)
    bd_correct = sum(s["correct"] for s in summary["breakdown_difficulty"].values())
    assert bd_correct == summary["correct"]


# ---------------------------------------------------------------------------
# format_summary() — conditional breakdown (missing fields)
# ---------------------------------------------------------------------------

def test_no_domain_breakdown_when_field_absent():
    """Results without 'domain' key should produce no domain breakdown."""
    stub_results = [
        {"id": "x1", "correct": True, "predicted": "00001", "expected": "00001"},
        {"id": "x2", "correct": False, "predicted": "00000", "expected": "00002"},
    ]
    stub_batch = {"results": stub_results, "total": 2, "correct": 1, "accuracy": 0.5}
    summary = format_summary(stub_batch)
    assert "breakdown_domain" not in summary


def test_no_difficulty_breakdown_when_field_absent():
    """Results without 'difficulty' key should produce no difficulty breakdown."""
    stub_results = [
        {"id": "x1", "correct": True, "predicted": "00001", "expected": "00001"},
    ]
    stub_batch = {"results": stub_results, "total": 1, "correct": 1, "accuracy": 1.0}
    summary = format_summary(stub_batch)
    assert "breakdown_difficulty" not in summary


def test_summary_with_limit():
    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=4)
    summary = format_summary(batch)
    assert summary["total"] == 4
    assert "breakdown_domain" in summary
    assert "breakdown_difficulty" in summary
