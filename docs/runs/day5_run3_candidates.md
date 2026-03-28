# Day5 Run3 — Candidate Count (N) Scaling

## Purpose

Scale the number of solver candidates N as a single controlled variable.
Answer Normalization (Run1) and Execution Retry (Run2) are both fixed.

---

## Change Variable

| Variable | Run1 | Run2 | Run3 |
|---|---|---|---|
| Answer Normalization | `format_answer()` — fixed | unchanged | unchanged |
| Execution Retry | 0 | configurable 0/1/2 | unchanged (fixed from Run2) |
| **Candidate count N** | 1 | 1 | **16 / 32 / 64** |

All other variables (solver, dataset, selection strategy) unchanged.

---

## Implementation

New functions in `src/day1_minimal_baseline/pipeline.py`:

| Symbol | Role |
|---|---|
| `generate_candidates(record, N)` | Generate N solver answers; `MemoryError` propagates (OOM fatal) |
| `select_by_majority(candidates)` | Majority vote; tie → lexicographically smallest |
| `run_one_with_candidates(record, N, max_retries, timeout_sec)` | N-candidate + retry wrapper |
| `run_batch_with_candidates(records, …)` | Batch runner; aggregates N and diversity stats |

`format_summary()` conditionally includes `candidate_stats` when batch
came from `run_batch_with_candidates()`.

---

## CLI Usage

```bash
# N=1 (backward compat)
PYTHONPATH=src python scripts/run_baseline_batch.py

# N=16 (Run3 comparison point 1)
PYTHONPATH=src python scripts/run_baseline_batch.py --num-candidates 16

# N=32
PYTHONPATH=src python scripts/run_baseline_batch.py --num-candidates 32

# N=64
PYTHONPATH=src python scripts/run_baseline_batch.py --num-candidates 64

# N=16 with Retry=1 (combined Run2+Run3 settings)
PYTHONPATH=src python scripts/run_baseline_batch.py --num-candidates 16 --max-retries 1
```

---

## Summary Fields Added

When `--num-candidates > 1`:

| Field | Description |
|---|---|
| `num_candidates_setting` | N used for this batch |
| `avg_candidate_diversity` | Mean (unique answers / N) across problems; 0→all same, 1→all different |

A higher `avg_candidate_diversity` indicates the solver is producing varied
outputs — useful for diagnosing whether increasing N is actually adding signal
or just repeating the same answer.

---

## Candidate Selection

**Strategy: majority vote with deterministic tie-breaking.**

- Count occurrences of each 5-digit answer across N candidates.
- Return the most frequent answer.
- Ties broken lexicographically (smallest answer wins).
- Empty candidate list raises `ValueError` — no silent fallback.

---

## OOM and Timeout Policy

| Error | Retried? | Note |
|---|---|---|
| `MemoryError` | **No** | OOM is deterministic at given N; retrying wastes time |
| `ExecTimeoutError` | **No** | 250s budget already exceeded |
| `RuntimeError`, `SyntaxError`, etc. | **Yes** (up to max_retries) | Transient errors |

---

## Adoption Criteria (reminder)

| Criterion | Threshold |
|---|---|
| Accuracy vs N=1 | Must improve monotonically (or show meaningful trend) |
| `avg_runtime_sec` | ≤ 250s per problem |
| `max_runtime_sec` | < 250s per problem |
| OOM | None |

---

## Rollback Condition

Revert to the largest stable N if:
- OOM occurs at N=X → lock at N=X−1 tier
- `avg_runtime_sec > 250s`
- Accuracy plateaus while runtime grows (N buys nothing)

---

## Placeholder Baseline (N=16, N=32, N=64)

With the placeholder solver, all candidates are `"00000"`:

| N | avg_candidate_diversity | accuracy | note |
|---|---|---|---|
| 1 | 1.000000 | 0.0000 | all identical (only 1 sample) |
| 16 | 0.062500 | 0.0000 | 1/16 unique |
| 32 | 0.031250 | 0.0000 | 1/32 unique |
| 64 | 0.015625 | 0.0000 | 1/64 unique |

`avg_candidate_diversity` becomes meaningful with a real stochastic solver.
