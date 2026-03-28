# AIMO3 Experiment Log Template

Copy this file and rename it `docs/runs/YYYYMMDD_<tag>.md` before filling in.

---

## Run Metadata

| Field              | Value |
|--------------------|-------|
| Date               | YYYY-MM-DD |
| Branch             | `codex/restart-clean` |
| Commit SHA         | `xxxxxxx` |
| Solver mode        | placeholder / llm / cli |
| Model (if llm/cli) | claude-haiku-4-5-20251001 / (subscription) |
| Dataset            | `data/shadow_eval.jsonl` v1.0 |
| Limit              | all (32) / N |
| `--num-candidates` | 1 |
| `--max-retries`    | 0 |
| `--timeout-sec`    | 250 / 300 |

---

## Command

```bash
PYTHONPATH=src python scripts/run_baseline_batch.py \
  --solver-mode cli \
  --timeout-sec 300
```

---

## Summary

| Metric                       | Value |
|------------------------------|-------|
| total                        |       |
| correct                      |       |
| accuracy                     |       |
| 5digit_compliance rate       |       |
| parse_failure_count          |       |
| parse_success_count          |       |
| retry_count_used             |       |
| exec_error_count             |       |
| avg_runtime_sec              |       |
| max_runtime_sec              |       |
| avg_candidate_diversity      |       |
| num_candidates_setting       |       |

**FLAGGED-E check:** accuracy > 0.70 → flag as possible contamination (see `docs/shadow_eval_v1.0_freeze.md`)

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

## Per-Record Results

```
id           domain         diff   pred   gold  ok?
----------------------------------------------------------
```

---

## Quality Checks

| Check | Result |
|---|---|
| exit code == 0 | |
| total == 32 | |
| 5digit_compliance == 1.0 | |
| parse_failure_count == 0 | |
| max_runtime_sec < timeout_sec | |
| accuracy < 0.70 (FLAGGED-E threshold) | |
| no all-same predicted column | |
| exec_error_count == 0 | |

---

## Notes

- What changed from the previous run?
- Known issues or surprises?
- Next steps?
