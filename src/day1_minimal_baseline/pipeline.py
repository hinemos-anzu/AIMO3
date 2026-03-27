"""Minimal evaluation pipeline.

Day1 goal: deterministic, comparable baseline.
Day2 addition: run_batch() for multi-record aggregation.
Day3 addition: format_summary() for human-readable breakdown.
Day4 addition: 5-digit enforcement in run_one(); compliance metric in format_summary().
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

    Both predicted and expected are guaranteed to be 5-digit strings.
    Raises ValueError if either cannot be normalised to 5 digits.
    """
    predicted = format_answer(solve_placeholder(record))
    expected = format_answer(record["answer"])

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


def _breakdown(results: list[dict[str, Any]], key: str) -> dict[Any, dict[str, Any]]:
    """Build a per-value breakdown dict for a single result field.

    Only counts entries where the field is present and not None.
    Returns {} if no entry has the field.
    """
    groups: dict[Any, list[bool]] = {}
    for r in results:
        val = r.get(key)
        if val is None:
            continue
        groups.setdefault(val, []).append(r["correct"])

    if not groups:
        return {}

    return {
        val: {
            "total": len(corrects),
            "correct": sum(corrects),
            "accuracy": sum(corrects) / len(corrects),
        }
        for val, corrects in sorted(groups.items(), key=lambda x: str(x[0]))
    }


def _is_5digit(value: Any) -> bool:
    """Return True iff value is a 5-character all-digit string."""
    return isinstance(value, str) and len(value) == 5 and value.isdigit()


def format_summary(batch: dict[str, Any]) -> dict[str, Any]:
    """Build an observable summary from run_batch() output.

    Always present:
        total, correct, accuracy
        answer_5digit_compliance — {compliant, total, rate}
            compliant: records where both predicted and expected are 5-digit strings
            rate:      compliant / total (float)

    Present only when the field exists in at least one result:
        breakdown_domain     — per-domain  total/correct/accuracy
        breakdown_difficulty — per-difficulty total/correct/accuracy

    Args:
        batch: return value of run_batch().

    Returns:
        summary dict (deterministic, comparable across runs).
    """
    results = batch["results"]
    total = batch["total"]

    compliant = sum(
        1 for r in results
        if _is_5digit(r.get("predicted")) and _is_5digit(r.get("expected"))
    )

    summary: dict[str, Any] = {
        "total": total,
        "correct": batch["correct"],
        "accuracy": batch["accuracy"],
        "answer_5digit_compliance": {
            "compliant": compliant,
            "total": total,
            "rate": compliant / total if total > 0 else 0.0,
        },
    }

    domain_bd = _breakdown(results, "domain")
    if domain_bd:
        summary["breakdown_domain"] = domain_bd

    difficulty_bd = _breakdown(results, "difficulty")
    if difficulty_bd:
        summary["breakdown_difficulty"] = difficulty_bd

    return summary
