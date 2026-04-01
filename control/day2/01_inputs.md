# AIMO3 Day2 Shared Inputs

Populate or update this file as evidence is collected.

## Required artifacts
### A. Local run logs
- Source: Kaggle / local execution logs
- Include lines showing:
  - `Starting Local Evaluation on 10 problems...`
  - `HarmonyError: Unexpected EOS while waiting for message header to complete`
  - traceback sections
  - `Consensus reached. Final Answer:`
  - `Final Score: 8 / 10`
  - absence or non-occurrence of `CRITICAL FAILURE` if supported by logs

### B. Production / Kaggle evidence
- Submission result screen or text note
- Any status, score, or error note
- Explicitly state whether this is objective evidence or user-reported context only

### C. Code snippets to review
Add or update snippets in `code/relevant_snippets/day2_snippets.md` for:
- `predict()`
- `_process_attempt`
- `_select_answer`
- `inference_server.serve()`
- exception handling
- fallback-like branches
- logging points

### D. Existing reports
- Gemini report should be stored in `control/day2/03_gemini_result.md`
- Claude audit should be stored in `control/day2/06_claude_audit_result.md`

## Current known observations
- Local run completed 10 problems.
- Multiple `HarmonyError` events were observed.
- Pipeline continued and emitted consensus answers.
- Local result reported `Final Score: 8 / 10`.
- `CRITICAL FAILURE` route was not observed in the reported local run.
- Kaggle `LB 37` is currently treated as user-reported context unless objective proof is attached.

## Important separation
Keep the following separate in all reports:
1. local pipeline success
2. production submission success
3. fail-fast behavior when all attempts fail
4. silent fallback removal audit
