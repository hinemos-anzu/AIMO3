# AIMO3 Experiment Log Template

Copy this file and rename it `docs/runs/YYYYMMDD_<tag>.md` before filling in.

---

## Run Metadata

| Field       | Value |
|-------------|-------|
| Date        | YYYY-MM-DD |
| Branch      | `codex/restart-clean` |
| Commit SHA  | `xxxxxxx` |
| Solver tag  | placeholder / rule-based / llm-X |
| Dataset     | `data/shadow_eval.jsonl` v1.0 |
| Limit       | all / N |

---

## Command

```bash
PYTHONPATH=src python scripts/run_baseline_batch.py --limit N
```

---

## Summary

| Metric   | Value |
|----------|-------|
| total    |       |
| correct  |       |
| accuracy |       |

---

## Domain Breakdown

| Domain        | total | correct | accuracy |
|---------------|-------|---------|----------|
| algebra       |       |         |          |
| combinatorics |       |         |          |
| geometry      |       |         |          |
| number_theory |       |         |          |

---

## Difficulty Breakdown

| Difficulty | total | correct | accuracy |
|------------|-------|---------|----------|
| 1          |       |         |          |
| 2          |       |         |          |

---

## Notes

- What changed from the previous run?
- Known issues or surprises?
- Next steps?
