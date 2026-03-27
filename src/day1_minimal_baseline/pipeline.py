"""Minimal evaluation pipeline.

Day1 goal: deterministic, comparable baseline.
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
