"""Minimal evaluation pipeline.

Day1 goal: deterministic, comparable baseline.
Day2 addition: run_batch() for multi-record aggregation.
Solver is a placeholder — returns "00000".
"""

from typing import Any


def solve_placeholder(record: dict[str, Any]) -> str:
    """Placeholder solver.

    Always returns '00000' (5-digit zero string).
    Replace this with a real solver in later days.
    """
    return "00000"


def format_answer(raw: str) -> str:
    """Ensure answer is exactly 5-digit zero-padded string.

    Raises:
        ValueError: raw cannot be interpreted as a non-negative integer.
    """
    try:
        value = int(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cannot convert answer to int: {raw!r}") from exc
    if value < 0:
        raise ValueError(f"Answer must be non-negative, got {value}")
    return f"{value:05d}"


def run_one(record: dict[str, Any]) -> dict[str, Any]:
    """Run the pipeline on a single record.

    Returns a result dict with keys:
        id, domain, difficulty, predicted, expected, correct
    """
    predicted = solve_placeholder(record)
    expected = record["answer"]  # already 5-digit in dataset

    return {
        "id": record["id"],
        "domain": record["domain"],
        "difficulty": record["difficulty"],
        "predicted": predicted,
        "expected": expected,
        "correct": predicted == expected,
    }


def run_batch(
    records: list[dict[str, Any]],
    limit: int | None = None,
) -> dict[str, Any]:
    """Run the pipeline on multiple records and aggregate results.

    Args:
        records: list of dataset records (from load_jsonl).
        limit:   if given, process only the first N records.
                 Must be >= 1 when specified.

    Returns a dict with keys:
        results  — list of run_one() outputs (in order)
        total    — number of records processed
        correct  — number of correct predictions
        accuracy — correct / total (float), or 0.0 when total == 0

    Raises:
        ValueError: limit is given but < 1.
    """
    if limit is not None and limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")

    subset = records[:limit] if limit is not None else records
    results = [run_one(r) for r in subset]
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = correct / total if total > 0 else 0.0

    return {
        "results": results,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
    }
