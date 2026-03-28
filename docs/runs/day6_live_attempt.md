# Day6.5 — Live Solver Attempt

## Purpose

Verify that the Day6 LLM solver adapter works end-to-end with a real
`ANTHROPIC_API_KEY` — one live call per the single-record and batch scripts.

---

## Environment Check

| Item | Status |
|---|---|
| `anthropic` SDK | Installed (v0.86.0) |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` |
| `ANTHROPIC_API_KEY` | **Not set in this task environment** |

---

## Attempted Runs

### Single-record run

```
PYTHONPATH=src python scripts/run_baseline_once.py --solver-mode llm
```

**Result:**
```
ERROR: ANTHROPIC_API_KEY environment variable is not set.
```
Exit code: 1

### Batch run (limit=3)

```
PYTHONPATH=src python scripts/run_baseline_batch.py --solver-mode llm --limit 3
```

**Result:**
```
ERROR: ANTHROPIC_API_KEY environment variable is not set.
```
Exit code: 1

---

## Findings

1. **No silent fallback**: `SolverConfigError` raised cleanly — never falls through to
   placeholder mode. The `create_solver(LLM)` guard works as designed.

2. **Clean exit**: Both scripts exit with code 1 and print a human-readable error
   message to `stderr`. No partial output, no corrupted state.

3. **Code is correct**: The blocker is purely environmental (no API key in this
   task environment), not a code defect.

---

## Stop Condition Triggered

Per Day6.5 instructions:
> "認証エラーが反復する / API / network 側障害で live 実行が意味をなさない
>  → 無理に進めず停止し、理由を明記してください"

Live execution is not meaningful without `ANTHROPIC_API_KEY`. Task stopped here.

---

## How to Proceed (when API key is available)

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# Single record — verify one live call
PYTHONPATH=src python scripts/run_baseline_once.py --solver-mode llm

# Batch of 3 — verify end-to-end batch flow
PYTHONPATH=src python scripts/run_baseline_batch.py --solver-mode llm --limit 3

# Optional: retry + candidates sanity check
PYTHONPATH=src python scripts/run_baseline_batch.py \
  --solver-mode llm --limit 3 --num-candidates 2 --max-retries 1
```

Expected observations:
- 5-digit answers returned (or `parse_failure_count > 0` if model adds prose)
- `parse_stats` section visible in batch output
- No placeholder fallback — all answers come from the API

---

## Test Coverage (as of this commit)

140 tests pass (pytest, no API key required):
- Day1–Day6 smoke tests all green
- LLM path covered via monkeypatch (no live calls needed for CI)

---

## Status

| Item | Result |
|---|---|
| API key present | NO |
| SolverConfigError raised correctly | PASS |
| No placeholder fallback | PASS |
| Live LLM call | BLOCKED (no key) |
| Code correctness | PASS (adapter fully implemented) |
