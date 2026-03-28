# Day5 Run2 — Execution Retry

## Purpose

Add Execution Retry as a single controlled variable on top of the Day4 baseline.
Answer Normalization (`format_answer()`, 5-digit zero-pad) is fixed from Day4 and
is not changed in this run.

---

## Change Variable

| Variable | Run1 (baseline) | Run2 |
|---|---|---|
| Answer Normalization | `format_answer()` — fixed | unchanged |
| Execution Retry | 0 (no retry) | configurable: 0 / 1 / 2 |

All other variables (solver, dataset, candidate count) are unchanged.

---

## Implementation

New functions in `src/day1_minimal_baseline/pipeline.py`:

| Symbol | Role |
|---|---|
| `ExecTimeoutError` | Raised when per-problem wall-clock exceeds `timeout_sec`. Never retried. |
| `run_one_with_retry(record, max_retries, timeout_sec)` | Wraps solver call with retry loop. Raises on exhaustion — no silent fallback. |
| `run_batch_with_retry(records, limit, max_retries, timeout_sec)` | Batch runner; aggregates retry / timing stats. |

`format_summary()` conditionally includes `retry_stats` when batch came from
`run_batch_with_retry()`.

---

## Retry Rules

- Retry fires on: any `Exception` from the solver (`SyntaxError`, `RuntimeError`,
  `ValueError`, etc.)
- Retry does NOT fire on: `ExecTimeoutError` — timeout is always fatal.
- Retry is bounded: `max_retries + 1` total attempts maximum.
- Exhausted retries raise `RuntimeError` explicitly — **no silent fallback**.
- Per-problem time limit: `timeout_sec=250.0` (default, matches Gemini 1-problem cap).

---

## CLI Usage

```bash
# Retry=0 (default, backward-compatible)
PYTHONPATH=src python scripts/run_baseline_batch.py

# Retry=1
PYTHONPATH=src python scripts/run_baseline_batch.py --max-retries 1

# Retry=2 with explicit timeout
PYTHONPATH=src python scripts/run_baseline_batch.py --max-retries 2 --timeout-sec 250
```

---

## Summary Fields Added

When `--max-retries >= 1`:

| Field | Description |
|---|---|
| `retry_count_used` | Total retries consumed across all problems |
| `exec_error_count` | Total solver exceptions caught |
| `avg_runtime_sec` | Mean per-problem wall-clock time |
| `max_runtime_sec` | Max per-problem wall-clock time (must stay < 250s) |
| `max_retries_setting` | The `--max-retries` value used |
| `timeout_sec_setting` | The `--timeout-sec` value used |

---

## Adoption Criteria (reminder)

| Criterion | Threshold |
|---|---|
| Accuracy | Must not decrease |
| `exec_error_count` | Should decrease with retry |
| `avg_runtime_sec` increase | ≤ +15% vs Retry=0 |
| `max_runtime_sec` | < 250s per problem |

---

## Rollback Condition

Revert to Retry=0 if:
- Any problem hits the 250s timeout
- Same error repeats across all retries (no improvement)
- Runtime increases with no accuracy gain

---

## Placeholder Baseline Result (Retry=2)

With the placeholder solver, no execution errors occur, so:

```
retry_count_used  : 0
exec_error_count  : 0
avg_runtime_sec   : ~0.000
max_runtime_sec   : ~0.000
```

These fields become meaningful when a real solver is plugged in.
