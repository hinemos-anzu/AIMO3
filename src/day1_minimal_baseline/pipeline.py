"""Minimal evaluation pipeline.

Day1 goal: deterministic, comparable baseline.
Day2 addition: run_batch() for multi-record aggregation.
Day3 addition: format_summary() for human-readable breakdown.
Day4 addition: 5-digit enforcement in run_one(); compliance metric in format_summary().
Day5 Run2 addition: run_one_with_retry() / run_batch_with_retry(); ExecTimeoutError.
Day5 Run3 addition: generate_candidates() / select_by_majority() /
                    run_one_with_candidates() / run_batch_with_candidates().
Day6 addition: solver injection (solver= param); parse_failure_count tracking;
               real LLM solver via solver.py adapter.
Solver is a placeholder by default — returns "00000".
"""

import time
from collections import Counter
from typing import Any, Callable


class ExecTimeoutError(RuntimeError):
    """Raised when a single problem exceeds its per-problem time limit.

    Never retried — always fatal for that problem.
    """


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


def run_one_with_retry(
    record: dict[str, Any],
    max_retries: int = 0,
    timeout_sec: float = 250.0,
    solver: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Run the solver with retry on execution errors.

    Retry fires on: any Exception from the solver call (SyntaxError,
    RuntimeError, ValueError, etc.).
    Retry does NOT fire on: ExecTimeoutError — timeout is always fatal.
    Silent fallback is forbidden — exhausted retries raise RuntimeError.

    Args:
        record:      single dataset record.
        max_retries: number of additional attempts after the first.
                     0 = no retry (same as run_one).  Must be >= 0.
        timeout_sec: per-problem wall-clock limit in seconds.
                     Checked before each attempt.  Must be > 0.
        solver:      callable (record) -> raw_str.  None = solve_placeholder.

    Returns a dict with the same keys as run_one() plus:
        retries_used       — attempts made beyond the first (0 = first try OK)
        exec_error_count   — number of failed attempts
        parse_failure_count — attempts that failed due to ValueError/TypeError
        elapsed_sec        — total wall-clock time for this record
        exec_errors        — list of error strings from failed attempts

    Raises:
        ValueError:       max_retries < 0 or timeout_sec <= 0.
        ExecTimeoutError: elapsed time exceeds timeout_sec.
        RuntimeError:     all attempts exhausted.
    """
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")
    if timeout_sec <= 0:
        raise ValueError(f"timeout_sec must be > 0, got {timeout_sec}")

    actual_solver = solver if solver is not None else solve_placeholder
    start = time.monotonic()
    exec_error_log: list[str] = []
    parse_failure_count = 0
    max_attempts = max_retries + 1

    for attempt in range(max_attempts):
        elapsed = time.monotonic() - start
        if elapsed > timeout_sec:
            raise ExecTimeoutError(
                f"{record['id']}: timeout {elapsed:.1f}s > {timeout_sec}s "
                f"before attempt {attempt}"
            )

        try:
            predicted = format_answer(actual_solver(record))
            expected = format_answer(record["answer"])
            elapsed = time.monotonic() - start
            return {
                "id": record["id"],
                "domain": record.get("domain"),
                "difficulty": record.get("difficulty"),
                "predicted": predicted,
                "expected": expected,
                "correct": predicted == expected,
                "retries_used": attempt,
                "exec_error_count": len(exec_error_log),
                "parse_failure_count": parse_failure_count,
                "elapsed_sec": round(elapsed, 6),
                "exec_errors": exec_error_log,
            }
        except ExecTimeoutError:
            raise  # timeout always propagates immediately
        except (ValueError, TypeError) as exc:
            parse_failure_count += 1
            exec_error_log.append(
                f"attempt={attempt} {type(exc).__name__}(parse): {exc}"
            )
        except Exception as exc:
            exec_error_log.append(
                f"attempt={attempt} {type(exc).__name__}: {exc}"
            )

    # All attempts exhausted — explicit failure, no silent fallback
    raise RuntimeError(
        f"{record['id']}: all {max_attempts} attempt(s) failed. "
        f"Errors: {exec_error_log}"
    )


def run_batch_with_retry(
    records: list[dict[str, Any]],
    limit: int | None = None,
    max_retries: int = 0,
    timeout_sec: float = 250.0,
    solver: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Run the pipeline on multiple records with per-problem retry.

    Aggregates retry and timing statistics across all records.

    Args:
        records:     list of dataset records (from load_jsonl).
        limit:       if given, process only the first N records (>= 1).
        max_retries: per-problem retry limit (0 = no retry).
        timeout_sec: per-problem wall-clock limit in seconds.
        solver:      callable (record) -> raw_str.  None = solve_placeholder.

    Returns a dict with the same base keys as run_batch() plus:
        retry_count_used     — total retries consumed across all records
        exec_error_count     — total execution errors across all records
        parse_failure_count  — total parse failures (ValueError/TypeError)
        avg_runtime_sec      — mean elapsed_sec across records
        max_runtime_sec      — maximum elapsed_sec across records
        max_retries_setting  — the max_retries value used
        timeout_sec_setting  — the timeout_sec value used

    Raises:
        ValueError:       limit < 1.
        ExecTimeoutError: any problem exceeds timeout_sec.
        RuntimeError:     any problem exhausts all retries.
    """
    if limit is not None and limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")

    subset = records[:limit] if limit is not None else records
    results = [
        run_one_with_retry(
            r, max_retries=max_retries, timeout_sec=timeout_sec, solver=solver
        )
        for r in subset
    ]
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = correct / total if total > 0 else 0.0
    elapsed_times = [r["elapsed_sec"] for r in results]

    return {
        "results": results,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "retry_count_used": sum(r["retries_used"] for r in results),
        "exec_error_count": sum(r["exec_error_count"] for r in results),
        "parse_failure_count": sum(r.get("parse_failure_count", 0) for r in results),
        "avg_runtime_sec": sum(elapsed_times) / total if total > 0 else 0.0,
        "max_runtime_sec": max(elapsed_times) if elapsed_times else 0.0,
        "max_retries_setting": max_retries,
        "timeout_sec_setting": timeout_sec,
    }


def generate_candidates(
    record: dict[str, Any],
    num_candidates: int,
    solver: Callable[[dict[str, Any]], str] | None = None,
) -> list[str]:
    """Generate num_candidates answer strings from the solver.

    With the placeholder (default), returns num_candidates copies of "00000".
    With a real solver this produces N independently sampled answers.

    Args:
        record:         single dataset record.
        num_candidates: number of samples to generate.  Must be >= 1.
        solver:         callable (record) -> raw_str.  None = solve_placeholder.

    Raises:
        ValueError:  num_candidates < 1, or solver output not parseable.
        MemoryError: OOM from the solver — propagates to caller (not caught).
    """
    if num_candidates < 1:
        raise ValueError(f"num_candidates must be >= 1, got {num_candidates}")
    actual_solver = solver if solver is not None else solve_placeholder
    return [format_answer(actual_solver(record)) for _ in range(num_candidates)]


def select_by_majority(candidates: list[str]) -> str:
    """Return the most frequent candidate; break ties by smallest value.

    Deterministic: ties resolved lexicographically (smallest answer wins).

    Raises:
        ValueError: candidates is empty.
    """
    if not candidates:
        raise ValueError("candidates list is empty")
    counts = Counter(candidates)
    return min(counts, key=lambda a: (-counts[a], a))


def run_one_with_candidates(
    record: dict[str, Any],
    num_candidates: int = 1,
    max_retries: int = 0,
    timeout_sec: float = 250.0,
    solver: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Run solver with N-candidate generation, majority vote, and optional retry.

    Fixed settings (Run1 + Run2):
        Answer normalisation: format_answer() — unchanged.
        Retry logic:          same as run_one_with_retry() — unchanged.

    Variable (Run3):
        num_candidates: number of solver samples per attempt.

    Day6:
        solver: inject a real LLM solver via solver.create_solver().

    MemoryError (OOM) is never retried — it is always re-raised immediately.
    ExecTimeoutError is never retried — always re-raised immediately.
    ValueError/TypeError (parse failures) are retried and counted separately.
    All other exceptions trigger a retry up to max_retries times.
    Exhausted retries raise RuntimeError — no silent fallback.

    Returns a result dict with the same keys as run_one_with_retry() plus:
        num_candidates_setting  — N used for this record
        candidate_diversity     — unique_candidates / N  (0.0–1.0)
        candidates              — all generated candidate strings (len == N)
        parse_failure_count     — attempts that failed due to parse error

    Raises:
        ValueError:       invalid arguments.
        ExecTimeoutError: elapsed time exceeds timeout_sec.
        MemoryError:      OOM during candidate generation.
        RuntimeError:     all retry attempts exhausted.
    """
    if num_candidates < 1:
        raise ValueError(f"num_candidates must be >= 1, got {num_candidates}")
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")
    if timeout_sec <= 0:
        raise ValueError(f"timeout_sec must be > 0, got {timeout_sec}")

    start = time.monotonic()
    exec_error_log: list[str] = []
    parse_failure_count = 0
    max_attempts = max_retries + 1

    for attempt in range(max_attempts):
        elapsed = time.monotonic() - start
        if elapsed > timeout_sec:
            raise ExecTimeoutError(
                f"{record['id']}: timeout {elapsed:.1f}s > {timeout_sec}s "
                f"before attempt {attempt}"
            )

        try:
            candidates = generate_candidates(record, num_candidates, solver=solver)
            predicted = select_by_majority(candidates)
            expected = format_answer(record["answer"])
            elapsed = time.monotonic() - start
            diversity = len(set(candidates)) / num_candidates
            return {
                "id": record["id"],
                "domain": record.get("domain"),
                "difficulty": record.get("difficulty"),
                "predicted": predicted,
                "expected": expected,
                "correct": predicted == expected,
                "retries_used": attempt,
                "exec_error_count": len(exec_error_log),
                "parse_failure_count": parse_failure_count,
                "elapsed_sec": round(elapsed, 6),
                "exec_errors": exec_error_log,
                "num_candidates_setting": num_candidates,
                "candidate_diversity": round(diversity, 6),
                "candidates": candidates,
            }
        except (ExecTimeoutError, MemoryError):
            raise  # these are always fatal — never retried
        except (ValueError, TypeError) as exc:
            parse_failure_count += 1
            exec_error_log.append(
                f"attempt={attempt} {type(exc).__name__}(parse): {exc}"
            )
        except Exception as exc:
            exec_error_log.append(
                f"attempt={attempt} {type(exc).__name__}: {exc}"
            )

    raise RuntimeError(
        f"{record['id']}: all {max_attempts} attempt(s) failed. "
        f"Errors: {exec_error_log}"
    )


def run_batch_with_candidates(
    records: list[dict[str, Any]],
    limit: int | None = None,
    num_candidates: int = 1,
    max_retries: int = 0,
    timeout_sec: float = 250.0,
    solver: Callable[[dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Run the full pipeline (candidates + retry) over multiple records.

    Returns the same base keys as run_batch_with_retry() plus:
        num_candidates_setting  — N used for this batch
        avg_candidate_diversity — mean per-problem candidate_diversity
        parse_failure_count     — total parse failures across all attempts

    Args:
        solver: callable (record) -> raw_str.  None = solve_placeholder.

    Raises:
        ValueError:       limit < 1 or invalid num_candidates / max_retries.
        ExecTimeoutError: any problem exceeds timeout_sec.
        MemoryError:      OOM on any problem (not retried).
        RuntimeError:     any problem exhausts all retries.
    """
    if limit is not None and limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")

    subset = records[:limit] if limit is not None else records
    results = [
        run_one_with_candidates(
            r,
            num_candidates=num_candidates,
            max_retries=max_retries,
            timeout_sec=timeout_sec,
            solver=solver,
        )
        for r in subset
    ]
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = correct / total if total > 0 else 0.0
    elapsed_times = [r["elapsed_sec"] for r in results]
    diversities = [r["candidate_diversity"] for r in results]

    return {
        "results": results,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "retry_count_used": sum(r["retries_used"] for r in results),
        "exec_error_count": sum(r["exec_error_count"] for r in results),
        "parse_failure_count": sum(r.get("parse_failure_count", 0) for r in results),
        "avg_runtime_sec": sum(elapsed_times) / total if total > 0 else 0.0,
        "max_runtime_sec": max(elapsed_times) if elapsed_times else 0.0,
        "max_retries_setting": max_retries,
        "timeout_sec_setting": timeout_sec,
        "num_candidates_setting": num_candidates,
        "avg_candidate_diversity": sum(diversities) / total if total > 0 else 0.0,
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

    # Retry stats — present when batch came from run_batch_with_retry()
    #               or run_batch_with_candidates()
    if "retry_count_used" in batch:
        summary["retry_stats"] = {
            "retry_count_used": batch["retry_count_used"],
            "exec_error_count": batch["exec_error_count"],
            "avg_runtime_sec": round(batch["avg_runtime_sec"], 4),
            "max_runtime_sec": round(batch["max_runtime_sec"], 4),
            "max_retries_setting": batch["max_retries_setting"],
            "timeout_sec_setting": batch["timeout_sec_setting"],
        }

    # Candidate stats — present only when batch came from run_batch_with_candidates()
    if "num_candidates_setting" in batch:
        summary["candidate_stats"] = {
            "num_candidates_setting": batch["num_candidates_setting"],
            "avg_candidate_diversity": round(batch["avg_candidate_diversity"], 6),
        }

    # Parse stats — present when batch includes parse_failure_count tracking
    if "parse_failure_count" in batch:
        summary["parse_stats"] = {
            "parse_failure_count": batch["parse_failure_count"],
            "parse_success_count": batch["total"],  # all completed records succeeded
        }

    return summary
