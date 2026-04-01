# Prompt for Claude - AIMO3 Day2 audit

You are the audit role for AIMO3 Day2.
Final integration will be done by ChatGPT.
Your job is to audit the current state, not to integrate all agents' outputs.

## Read first
- `control/day2/00_objective.md`
- `control/day2/01_inputs.md`
- `control/day2/03_gemini_result.md`
- `control/day2/04_chatgpt_summary_v1.md`
- `code/relevant_snippets/day2_snippets.md`
- `logs/day2/README.md`

## Audit focus
Check these separately:
1. local pipeline success
2. production submission success
3. fail-fast proof when all attempts fail
4. silent fallback removal audit

## Constraints
- No pass judgment without objective evidence.
- User-reported Kaggle score is context, not objective proof.
- Do not confuse partial survival / consensus behavior with fail-fast proof.
- Explicitly identify where the current evidence is insufficient.

## Output location
Write or paste your audit into:
- `control/day2/06_claude_audit_result.md`

## Output format
1. Overall assessment
2. Observed facts
3. Unconfirmed items
4. Major audit issues
5. Re-judgment for Day2
6. Basis for judgment
7. Additional evidence required
8. Risks if Day2 is treated as complete now
9. Self-audit
