# Day6 — Real Solver Connection

## Purpose

Graduate from placeholder solver to a real LLM solver, while keeping the
Day1–Day5 evaluation infrastructure (normalization, retry, candidates, summary)
fully intact and solver-agnostic.

---

## What Changed

| Component | Before Day6 | After Day6 |
|---|---|---|
| Solver | `solve_placeholder()` hardcoded | Injected via `solver=` param (Callable) |
| Solver modes | placeholder only | `"placeholder"` / `"llm"` via `create_solver()` |
| Missing API key | n/a | `SolverConfigError` raised explicitly — no silent fallback |
| parse_failure_count | not tracked | Tracked per-record and aggregated at batch level |
| Summary | no parse_stats | `parse_stats` added (conditional, when batch supports it) |

---

## New Module: `src/day1_minimal_baseline/solver.py`

```python
from day1_minimal_baseline.solver import create_solver, PLACEHOLDER, LLM

solver = create_solver(PLACEHOLDER)           # no API key needed
solver = create_solver(LLM, model="...")      # requires ANTHROPIC_API_KEY
```

| Mode | Behaviour |
|---|---|
| `"placeholder"` | Returns `"00000"` for every problem (Day1–Day5 baseline) |
| `"llm"` | Calls Anthropic Claude API with problem metadata; returns raw text |

**LLM prompt content** (minimal — no full problem text in shadow_eval_v1.0):
- `source` (e.g. "2021 AIME I #5")
- `domain` (algebra / combinatorics / geometry / number_theory)
- `difficulty` (1 or 2)
- `notes` (Japanese hint)

Full problem text is not in the dataset. Accuracy will be limited until
problem text is added to shadow_eval.

---

## Solver Injection Points

`solver=` parameter added (default `None` → `solve_placeholder`) to:
- `generate_candidates(record, N, solver=None)`
- `run_one_with_retry(record, …, solver=None)`
- `run_batch_with_retry(records, …, solver=None)`
- `run_one_with_candidates(record, …, solver=None)`
- `run_batch_with_candidates(records, …, solver=None)`

All existing calls without `solver=` continue to work identically.

---

## CLI Usage

```bash
# Placeholder (backward compatible, no API key)
PYTHONPATH=src python scripts/run_baseline_once.py
PYTHONPATH=src python scripts/run_baseline_batch.py --limit 5

# LLM solver (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
PYTHONPATH=src python scripts/run_baseline_once.py --solver-mode llm
PYTHONPATH=src python scripts/run_baseline_batch.py --solver-mode llm --limit 5
PYTHONPATH=src python scripts/run_baseline_batch.py --solver-mode llm --num-candidates 4

# LLM + retry + candidates (full Day5 Run3 settings)
PYTHONPATH=src python scripts/run_baseline_batch.py \
  --solver-mode llm --num-candidates 4 --max-retries 1 --timeout-sec 250
```

---

## Environment Constraints (as of Day6 commit)

| Item | Status |
|---|---|
| `anthropic` SDK | Installed (v0.86.0) |
| `ANTHROPIC_BASE_URL` | Set (`https://api.anthropic.com`) |
| `ANTHROPIC_API_KEY` | **Not set in this environment** |
| Live LLM calls | Not possible without API key |
| Adapter infrastructure | Fully implemented and tested (monkeypatch) |

**To run with real LLM:** set `ANTHROPIC_API_KEY` and use `--solver-mode llm`.

---

## parse_failure_count

Tracks how many solver invocations produced output that could not be parsed
as a non-negative integer by `format_answer()` (ValueError/TypeError).

Meaning:
- `parse_failure_count == 0` → solver always returned parseable output
- `parse_failure_count > 0` → solver returned non-numeric text on some attempts
  (e.g. "The answer is 42" instead of just "42")

With placeholder: always 0.
With LLM: may be > 0 if model adds prose around the number.

---

## Rollback Plan

If LLM solver proves unstable (high parse_failure_count, high retry usage,
or unexpected accuracy drop vs. oracle):
1. Switch back to `--solver-mode placeholder`
2. The placeholder path is identical to Day1–Day5 behaviour
3. No code changes required — mode is a runtime flag

---

## Known Limitations

1. **No problem text in dataset**: shadow_eval_v1.0 has metadata only.
   The LLM prompt uses source/domain/difficulty/notes, not the full problem.
   Accuracy will likely be low even with a capable model.

2. **API key dependency**: LLM mode requires `ANTHROPIC_API_KEY` to be set.
   The adapter raises `SolverConfigError` (not a silent fallback) if missing.

3. **N candidates with LLM = N API calls per problem**: latency and cost
   scale linearly with `--num-candidates`. Use small N for initial testing.

4. **parse_failure_count is per-attempt, not per-record**: a record that
   fails parsing on attempt 1 but succeeds on attempt 2 contributes
   `parse_failure_count=1` to the total — it is still counted as success
   in `parse_success_count`.
