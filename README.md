# AIMO3 Day1 Minimal Baseline

Day1 goal is a **comparable baseline foundation**, not max accuracy.

## Quick start

```bash
python scripts/run_baseline_once.py
```

Expected output: one JSON row with 5-digit `answer`.

## Docs guide

- Shadow eval definition: [`docs/shadow_eval_spec.md`](docs/shadow_eval_spec.md)
- Executor policy: [`docs/executor_policy.md`](docs/executor_policy.md)
- Verifier policy: [`docs/verifier_policy.md`](docs/verifier_policy.md)
- Experiment logging template: [`docs/experiment_template.md`](docs/experiment_template.md)
- Submission checks: [`docs/submission_checklist.md`](docs/submission_checklist.md)

## Notes

- Current baseline is intentionally minimal (`generator + executor + verifier/selector` placeholder).
- TODOs are left in docs/modules for Day2 extensions (verifier/reranker/heavier generator).

## GitHub branch sync (when changes do not appear on GitHub)

This environment edits your **local git repo** first. If nothing appears on GitHub, check the following:

```bash
git branch --show-current
git remote -v
git push -u origin codex/prepare-repo-for-aimo3-day-1
```

- If `git remote -v` is empty, connect this repo to GitHub remote first.
- If push is denied, check token/SSH auth and repo write permissions.

