# AIMO3 Day2 Objective

## Purpose
Day2 is **not** a score-maximization day.
Day2 is the day to confirm that the **production submission path is valid**.

## Primary checks
1. Confirm the production submission path through `predict()`.
2. Confirm the production path through `inference_server.serve()`.
3. Audit that silent fallback has been structurally removed.
4. Separate and identify any `Submission Error`, `timeout`, `crash`, or `0 score` outcomes.
5. Keep local success, production success, fail-fast behavior, and silent-fallback audit as distinct concerns.

## Completed before Day2
- offline wheel install
- required imports
- vLLM startup
- openai_harmony operation
- model path resolution
- integer output on local real data
- log output to `/kaggle/working/`

## Governance
- Final orchestration and integration: ChatGPT
- Audit role: Claude
- Implementation / execution role: Gemini or other code agent as instructed
- Kaggle execution and submission: user

## Evidence rules
- No pass judgment without objective evidence.
- User self-report is useful context, but not objective proof.
- Dummy / placeholder / toy / local outputs must never be treated as real production proof.
- Any inference or assumption must be explicitly labeled.
