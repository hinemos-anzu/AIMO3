# AIMO3 Experiment Log — 2026-03-27 placeholder

Filled example for `docs/experiment_log_template.md`.
This run uses the Day4 baseline with the placeholder solver.

---

## Run Metadata

| Field       | Value |
|-------------|-------|
| Date        | 2026-03-27 |
| Branch      | `codex/restart-clean` |
| Commit SHA  | `0265ee3a494bf0819ab9b16ef89b0deca37500b3` (Day3) |
| Solver tag  | placeholder (returns `"00000"` for every problem) |
| Dataset     | `data/shadow_eval.jsonl` v1.0 |
| Limit       | all (32 problems) |

---

## Command

```bash
PYTHONPATH=src python scripts/run_baseline_batch.py
```

---

## Summary

| Metric                  | Value  |
|-------------------------|--------|
| total                   | 32     |
| correct                 | 0      |
| accuracy                | 0.0000 |
| 5digit_compliance rate  | 1.0000 |

All 32 predicted answers and all 32 expected answers are valid 5-digit
strings — compliance rate is 1.0.  Accuracy is 0 because the placeholder
solver always returns `"00000"` regardless of the problem.

---

## Domain Breakdown

| Domain        | total | correct | accuracy |
|---------------|-------|---------|----------|
| algebra       | 8     | 0       | 0.0000   |
| combinatorics | 8     | 0       | 0.0000   |
| geometry      | 8     | 0       | 0.0000   |
| number_theory | 8     | 0       | 0.0000   |

---

## Difficulty Breakdown

| Difficulty | total | correct | accuracy |
|------------|-------|---------|----------|
| 1          | 16    | 0       | 0.0000   |
| 2          | 16    | 0       | 0.0000   |

---

## Notes

- Baseline run. No real solver attached yet.
- All answer outputs are 5-digit (`format_answer()` enforced in `run_one()`).
- `answer_5digit_compliance` = 1.0 confirms the enforcement is working.
- Next step: replace `solve_placeholder()` with a real solver and compare
  accuracy numbers against this record.
