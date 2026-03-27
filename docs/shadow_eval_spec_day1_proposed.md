# Shadow Eval Spec (Day1 Proposed)

## Purpose

Shadow eval is the **Day1 comparison anchor**.
Its role is to let us compare runs without relying on public LB and without drifting into contamination-driven iteration.

Principles:
- do not use public LB as the main selection signal
- avoid contamination
- do not start exploratory tuning before shadow eval is fixed
- keep experiments one-variable-at-a-time
- do not blur toy/mock data and real comparison data

## File

- Canonical path: `data/shadow_eval.jsonl`

## Day1 Status

Current repository state still uses a **toy placeholder dataset** for wiring checks.
That placeholder is useful for smoke testing only.
It is **not** the intended final Day1 comparison set.

Therefore, distinguish the following clearly:

### 1. Toy / smoke-check shadow eval
Purpose:
- confirm the pipeline runs end-to-end
- confirm JSONL loading works
- confirm 5-digit answer formatting works

Allowed characteristics:
- very small row count
- trivial arithmetic or mock prompts
- used only for wiring / test validation

Not allowed use:
- baseline comparison decision making
- experiment selection
- claiming Day1 baseline quality

### 2. Real Day1 comparison shadow eval
Purpose:
- fixed comparison set for Day1 baseline runs
- compare small implementation changes under a stable setup

Required characteristics:
- fixed file contents during Day1 comparisons
- no silent substitution with toy/mock data
- not derived from public test labels
- prepared with contamination awareness
- used before any exploratory tuning is accepted

## Current Minimal Schema

Current runnable code expects JSONL rows with at least:
- `id` (string)
- `problem` (string)

Example:

```json
{"id":"shadow-0001","problem":"Compute 1+1."}
```

## Intended Day1 Schema Policy

### Required fields
- `id`: stable string identifier
- `problem`: problem text used as model input

### Optional fields for later expansion
These are **not required for the current minimal runner** and should not be silently assumed.
Potential future fields may include:
- `source`
- `domain`
- `difficulty`
- `split`
- `notes`
- `contamination_checked`

If any optional field is introduced later:
- update this spec first
- update the reader/validator explicitly
- do not rely on fallback defaults without logging

## Real vs Toy Boundary

The repository must keep the distinction explicit.

Rules:
- toy data must be labeled as toy/mock/smoke-check in docs or filenames
- real Day1 comparison data must not be described with placeholder wording
- scripts/tests must not silently switch between toy and real inputs
- if a toy dataset is used, that fact must be obvious from command, config, or output

## Contamination Policy (Day1)

Minimum Day1 rules:
- do not build shadow eval from public test answers
- do not use leaked or memorized answer sets
- do not tune against public LB and then backfill the rationale into shadow eval
- if provenance is unclear, mark the dataset as **untrusted for comparison use**

Current status:
- contamination handling is only partially specified
- a stricter provenance/check workflow is still pending

## Freeze Policy

Before exploratory experiments begin, the real Day1 comparison shadow eval must be frozen.

Freeze means:
- row set fixed
- row order fixed unless order is explicitly defined as irrelevant
- schema fixed
- any later modification requires a changelog note

Recommended practice:
- record the row count
- record the file hash or commit SHA
- note whether the file is toy or real

## Validation Requirements

Any script that claims to run against shadow eval should at minimum validate:
- file exists
- file is valid JSONL
- each used row has `id` and `problem`
- duplicate `id` values are rejected or explicitly reported
- no silent fallback to another dataset path

## Day1 Completion Criteria for Shadow Eval

Shadow eval is considered ready for Day1 comparison use only when all of the following are true:
- a real comparison dataset exists at the canonical path, or an explicitly named alternative path is adopted
- toy vs real status is documented
- schema is fixed and matches the runner
- provenance/contamination status is documented at least at a basic level
- the runner does not silently fall back to placeholder data

## Out of Scope for Day1

The following can wait until Day2 or later:
- sophisticated split strategy
- domain balancing automation
- reranker/verifier-aware shadow eval design
- advanced contamination scanners

## Next Required Actions

1. Replace or supplement the current toy placeholder with a real Day1 comparison set.
2. Add explicit toy/real labeling in commands, config, or docs.
3. Add dataset validation so missing required fields or duplicate ids fail loudly.
4. Record freeze metadata once the real comparison set is chosen.
