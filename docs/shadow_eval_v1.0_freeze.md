# shadow_eval_v1.0 — Freeze Note

## Status: FROZEN

This document records the formal freeze of `data/shadow_eval.jsonl` as
version `shadow_eval_v1.0`.  The dataset must not be modified after this
point.  Any future change requires a new version tag (e.g. `v1.1`).

---

## Verification Result

Verified by `scripts/verify_shadow_eval.py` on 2026-03-27.

```
Checked 32 records.
PASS
```

All checks passed:

| Check | Result |
|---|---|
| Total record count == 32 | PASS |
| `answer_raw` ∈ [0, 99999] for all records | PASS |
| `answer == str(answer_raw).zfill(5)` for all records | PASS |
| Domain distribution (algebra/combinatorics/geometry/number_theory == 8 each) | PASS |
| Difficulty distribution (level 1 == 16, level 2 == 16) | PASS |
| Mismatches | 0 |

---

## Dataset Summary

| Field | Value |
|---|---|
| File | `data/shadow_eval.jsonl` |
| Version | `shadow_eval_v1.0` |
| Total problems | 32 |
| Sources | 2021 AIME I, 2022 AIME I, 2022 AIME II |
| Domains | algebra (8), combinatorics (8), geometry (8), number_theory (8) |
| Difficulty levels | 1 (16 problems), 2 (16 problems) |
| Answer format | 5-digit zero-padded string (`zero_pad_5`) |
| `answer_raw` range | [4, 834] |
| `contamination_checked` | true (all records) |
| `contamination_risk` | medium (all records) |

---

## Contamination Policy

All 32 problems are sourced from publicly available AIME competitions
(2021–2022) on Art of Problem Solving.  All records carry
`contamination_risk: "medium"` — meaning overlap with LLM training data
is plausible but not confirmed.

**Evaluation note:** If a solver achieves accuracy > 70 % on this dataset,
treat the result as **FLAGGED-E** (possible training data contamination)
and cross-validate on a held-out or later-competition dataset before
publishing results.

---

## Freeze Instructions

- Do **not** edit `data/shadow_eval.jsonl` after this tag.
- Do **not** add, remove, or reorder records.
- Do **not** change `answer_raw`, `answer`, or `answer_transform` fields.
- To fix a confirmed error, create `shadow_eval_v1.1` with a new tag and
  a new freeze note.

---

## Git Tag

```
shadow_eval_v1.0
```

Verify:
```bash
git show shadow_eval_v1.0
```
