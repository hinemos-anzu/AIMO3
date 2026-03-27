# CLAUDE.md — AI Assistant Guide for AIMO3

## Repository Overview

**AIMO3** is a shadow evaluation dataset repository for the AI Math Olympiad benchmark. It contains a curated set of competition mathematics problems used to evaluate AI model performance on mathematical reasoning tasks.

This is a **data-only repository** — there is no source code, build system, or runtime environment.

---

## Repository Structure

```
AIMO3/
├── CLAUDE.md                   # This file
├── .gitkeep                    # Empty placeholder
└── data/
    ├── .gitkeep
    └── shadow_eval.jsonl       # Primary dataset (32 AIME problems)
```

---

## Dataset: `data/shadow_eval.jsonl`

### Format

JSONL (JSON Lines) — one JSON object per line.

### Schema

| Field                  | Type    | Description |
|------------------------|---------|-------------|
| `id`                   | string  | Unique problem ID in `{domain}_{index}` format (e.g. `alg_001`) |
| `source`               | string  | Competition name and problem number (e.g. `"2021 AIME I #5"`) |
| `source_url`           | string  | Art of Problem Solving wiki URL for the problem |
| `domain`               | string  | Math domain: `algebra`, `combinatorics`, `geometry`, or `number_theory` |
| `difficulty`           | integer | Difficulty tier: `1` (easier) or `2` (harder) |
| `answer_raw`           | integer | Numeric answer as-is |
| `answer`               | string  | Zero-padded 5-digit answer string (AIME format, e.g. `"00031"`) |
| `answer_transform`     | string  | Transform applied to produce `answer`; always `"zero_pad_5"` |
| `contamination_checked`| boolean | Whether contamination check was performed; always `true` |
| `contamination_risk`   | string  | Assessment of training data overlap risk; all currently `"medium"` |
| `notes`                | string  | Japanese-language description of the problem focus/technique |
| `shadow_eval_version`  | string  | Dataset version; current value `"v1.0"` |

### Dataset Composition

- **Total problems:** 32
- **Domains:** 4 (algebra, combinatorics, geometry, number_theory) — 8 problems each
- **Difficulty levels:** 2 — 16 problems per level
- **Sources:** AIME I/II competitions from 2021 and 2022

### ID Scheme

| Domain        | Abbreviation | Example IDs          |
|---------------|--------------|----------------------|
| Algebra       | `alg`        | `alg_001` – `alg_008` |
| Combinatorics | `comb`       | `comb_001` – `comb_008` |
| Geometry      | `geo`        | `geo_001` – `geo_008` |
| Number Theory | `nt`         | `nt_001` – `nt_008` |

---

## Data Conventions

- **Answer format:** All answers are zero-padded to 5 digits (`answer_transform: "zero_pad_5"`), matching AIME competition scoring conventions.
- **IDs:** Use `{domain_abbrev}_{zero_padded_3_digit_index}` (e.g. `alg_001`, not `alg_1`).
- **Notes field:** Written in Japanese; describes the mathematical technique or key concept being tested.
- **Versioning:** Dataset version is tracked via `shadow_eval_version`. Current version: `v1.0`.
- **Contamination:** All problems are checked for training data contamination. All are rated `medium` risk.
- **File naming:** Use underscores, no spaces (e.g. `shadow_eval.jsonl`, not `shadow eval.jsonl`).

---

## Development Workflow

### Branch Strategy

All development happens on dedicated feature branches. The main/default branch should not be committed to directly.

Current development branch: `claude/add-claude-documentation-0Oaao`

### Making Changes to the Dataset

1. Edit `data/shadow_eval.jsonl` — one JSON object per line, no trailing commas.
2. Validate JSON: each line must be parseable as a standalone JSON object.
3. Maintain consistent field ordering: `id`, `source`, `source_url`, `domain`, `difficulty`, `answer_raw`, `answer`, `answer_transform`, `contamination_checked`, `contamination_risk`, `notes`, `shadow_eval_version`.
4. Commit with a descriptive message referencing the domain and change type.

### Validation Checklist (when adding/modifying problems)

- [ ] `answer` is exactly 5 characters, zero-padded numeric string
- [ ] `answer_transform` is `"zero_pad_5"`
- [ ] `id` follows `{abbrev}_{index}` format with 3-digit zero-padded index
- [ ] `domain` is one of: `algebra`, `combinatorics`, `geometry`, `number_theory`
- [ ] `difficulty` is `1` or `2`
- [ ] `contamination_checked` is `true` (must be verified before adding)
- [ ] `source_url` points to a valid Art of Problem Solving wiki page
- [ ] No trailing newline issues; file ends with a single newline after last record

### Git Commit Style

Use descriptive messages indicating what changed:
```
Add geometry problem geo_009 from 2022 AIME II #12
Update contamination_risk for nt_003 and nt_004
Fix zero-padding for comb_007 answer field
```

---

## Key Notes for AI Assistants

- This repository has **no code to execute** — do not attempt to run, build, or test anything.
- When adding new problems, always verify the `source_url` is a real AoPS problem page before committing.
- The `notes` field is intentionally in Japanese; do not translate it unless explicitly asked.
- Do not rename or restructure the `data/` directory — downstream evaluation pipelines may depend on this path.
- The duplicate file `shadow eval.jsonl` (with a space) at the repository root is a legacy artifact and should be removed if encountered.
- `shadow_eval_version` should only be incremented when the dataset schema or methodology changes significantly, not for individual problem additions.
