"""AIMO3 Solver/Verifier patch utilities (v2).

This module provides drop-in logic to apply the v2 ranking/verifier upgrades:
- true soft ranking (no early break)
- tri-state verifier verdict
- weaker verifier impact via additive bonuses
- reduced majority effect
- richer attempt/candidate logging
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional
import json
import math
import os
import re


@dataclass
class VerifierResult:
    verdict: str  # VALID | INVALID | UNVERIFIED
    tool_output: str
    verifier_code: str
    quality_score: float
    uses_candidate: bool
    has_assert: bool
    has_nontrivial_assert: bool
    condition_reference: bool
    contradiction_found: bool
    error_detected: bool


@dataclass
class CandidateScore:
    answer: int
    votes: int
    base_score: float
    majority_answer_flag: int
    verifier_verdict: str
    verifier_bonus: float
    small_case_consistency_score: float
    composite_score: float
    selected_flag: int = 0


def build_system_prompts_v2() -> List[str]:
    """Persona set based on search method (not writing style)."""
    return [
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Pure algebra derivation.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Invariant and parity reasoning.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Modular arithmetic and number theory.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Small-case brute force then generalize with proof.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Full enumeration when feasible.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: DP/recursion counting.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: CSP/ILP/SAT style modeling and solve.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Graph/state search with BFS/DFS.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Counterexample-first falsification.",
        "You are an IMO solver. Final answer in \\boxed{}. [STYLE]: Bounds/elimination/pruning.",
    ]


def tir_capabilities_block() -> str:
    return (
        "When using Python, prefer concrete tools: "
        "itertools.product/combinations/permutations, collections.Counter/defaultdict, "
        "functools.lru_cache, sympy.factorint/divisors/solve/diophantine, math.gcd, "
        "BFS/DFS templates, ILP/CSP if feasible, and small-case consistency checks."
    )


def verifier_prompt_v2(counterexample_mode: bool = False) -> str:
    if counterexample_mode:
        return (
            "You are a strict Mathematical Auditor. Try to falsify the proposed answer. "
            "Search for one contradiction, impossible condition, or mismatch using Python assertions. "
            "If no decisive proof is found, do not claim VALID; leave it UNVERIFIED."
        )
    return (
        "You are a strict Mathematical Auditor. Verify via backward checking against constraints. "
        "Use explicit assert statements and avoid tautologies."
    )


def allocate_problem_budget(
    notebook_time_left: float,
    problems_remaining: int,
    attempts: int,
    base_problem_timeout: float,
    high_problem_timeout: float,
    baseline_attempts: int = 10,
) -> float:
    """Auto-rebalance timeout budget for attempts variants (10/16/20)."""
    raw_budget = max(
        base_problem_timeout,
        min(
            notebook_time_left - max(0, problems_remaining - 1) * base_problem_timeout,
            high_problem_timeout,
        ),
    )
    per_attempt = raw_budget / max(1, baseline_attempts)
    scaled = per_attempt * max(1, attempts)
    return min(high_problem_timeout, max(base_problem_timeout, scaled))


def evaluate_verifier_quality(problem: str, candidate_ans: int, verifier_code: str) -> Dict[str, Any]:
    code = verifier_code or ""
    code_compact = re.sub(r"\s+", "", code.lower())

    uses_candidate = str(candidate_ans) in code
    has_assert = "assert" in code_compact
    tautology = any(
        token in code_compact
        for token in ["asserttrue", "assert1==1", "assert0==0", "assertx==x", "asserta==a"]
    )
    has_nontrivial_assert = has_assert and not tautology

    problem_tokens = {tok for tok in re.findall(r"[a-zA-Z]{3,}", problem.lower()) if len(tok) > 3}
    code_tokens = set(re.findall(r"[a-zA-Z]{3,}", code.lower()))
    overlap = len(problem_tokens.intersection(code_tokens))
    condition_reference = overlap >= 2

    quality_score = 0.0
    quality_score += 0.30 if uses_candidate else 0.0
    quality_score += 0.25 if has_assert else 0.0
    quality_score += 0.25 if has_nontrivial_assert else 0.0
    quality_score += 0.20 if condition_reference else 0.0

    return {
        "uses_candidate": uses_candidate,
        "has_assert": has_assert,
        "has_nontrivial_assert": has_nontrivial_assert,
        "condition_reference": condition_reference,
        "quality_score": round(quality_score, 4),
        "is_tautology_like": tautology,
    }


def classify_verifier_result(
    tool_output: str,
    quality: Dict[str, Any],
    contradiction_found: bool,
) -> str:
    txt = tool_output or ""
    error_detected = any(x in txt for x in ["[ERROR]", "Traceback", "AssertionError", "Error:"])
    if error_detected or contradiction_found:
        return "INVALID"
    if quality["quality_score"] >= 0.75 and quality["has_nontrivial_assert"] and quality["uses_candidate"]:
        return "VALID"
    return "UNVERIFIED"


def small_case_consistency_score(problem: str, answer: int) -> float:
    """Framework placeholder: return neutral score unless plug-in checker exists."""
    _ = (problem, answer)
    return 0.0


def select_answer_v2(
    results: Iterable[Dict[str, Any]],
    problem_text: str,
    gold_answer: Optional[int],
    problem_id: str,
    verify_fn,
    log_dir: str,
) -> int:
    """True soft-ranking selector over all candidates (no early exit)."""
    os.makedirs(os.path.join(log_dir, "ranker_eval"), exist_ok=True)
    os.makedirs(os.path.join(log_dir, "recall_eval"), exist_ok=True)

    ans_weights: Dict[int, float] = defaultdict(float)
    ans_votes: Dict[int, int] = defaultdict(int)
    valid_candidates: List[int] = []

    normalized_results = list(results)
    for r in normalized_results:
        ans = r.get("Answer")
        if ans is None:
            continue
        entropy = float(r.get("Entropy", float("inf")))
        base_weight = 1.0 / max(entropy, 1e-9)
        valid_candidates.append(ans)
        ans_weights[ans] += base_weight
        ans_votes[ans] += 1

    scored = [
        {"answer": a, "votes": ans_votes[a], "base_score": w}
        for a, w in ans_weights.items()
    ]
    scored.sort(key=lambda x: x["base_score"], reverse=True)

    recall_hit = int(gold_answer in set(valid_candidates)) if gold_answer is not None else 0
    majority_answer = Counter(valid_candidates).most_common(1)[0][0] if valid_candidates else None
    majority_correct = int(majority_answer == gold_answer) if gold_answer is not None else 0

    candidate_scores: List[CandidateScore] = []

    # Additive scoring (safer than multiplicative).
    verdict_bonus_map = {"VALID": 0.40, "UNVERIFIED": 0.10, "INVALID": -0.20}
    majority_bonus = 0.0  # intentionally disabled in v2

    best_answer = 0
    best_score = -float("inf")

    for cand in scored:
        ans = cand["answer"]
        verifier: VerifierResult = verify_fn(problem_text, ans)
        scc = small_case_consistency_score(problem_text, ans)
        verifier_bonus = verdict_bonus_map.get(verifier.verdict, 0.0)

        composite = (
            cand["base_score"]
            + verifier_bonus
            + majority_bonus * int(ans == majority_answer)
            + scc
        )

        row = CandidateScore(
            answer=ans,
            votes=cand["votes"],
            base_score=round(cand["base_score"], 6),
            majority_answer_flag=int(ans == majority_answer),
            verifier_verdict=verifier.verdict,
            verifier_bonus=verifier_bonus,
            small_case_consistency_score=scc,
            composite_score=round(composite, 6),
        )
        candidate_scores.append(row)

        if composite > best_score:
            best_score = composite
            best_answer = ans

    for row in candidate_scores:
        row.selected_flag = int(row.answer == best_answer)

    with open(os.path.join(log_dir, "ranker_eval", "per_problem_candidate_scores.jsonl"), "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "problem_id": problem_id,
                    "gold_answer": gold_answer,
                    "majority_answer": majority_answer,
                    "ranking_selector_answer": best_answer,
                    "ranking_scores": [asdict(r) for r in candidate_scores],
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    summary = {
        "problem_id": problem_id,
        "attempts": len(normalized_results),
        "gold_answer": gold_answer,
        "candidate_answers": sorted(set(valid_candidates)),
        "recall_at_k_hit": recall_hit,
        "candidate_unique_count": len(set(valid_candidates)),
        "majority_answer": majority_answer,
        "majority_is_correct": majority_correct,
        "ranking_selector_answer": best_answer,
        "ranking_is_correct": int(best_answer == gold_answer) if gold_answer is not None else 0,
    }
    with open(os.path.join(log_dir, "recall_eval", "recall_summary.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    return best_answer


def append_attempt_log_csv(log_dir: str, rows: Iterable[Dict[str, Any]]) -> None:
    os.makedirs(os.path.join(log_dir, "style_eval"), exist_ok=True)
    path = os.path.join(log_dir, "style_eval", "per_attempt_style.csv")
    header = (
        "problem_id,domain,attempt_idx,style_name,is_tir,answer,answer_is_correct,"
        "used_python,python_error,entropy,verifier_verdict,verifier_quality_score,selected_final\n"
    )
    file_exists = os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write(header)
        for r in rows:
            f.write(
                "{problem_id},{domain},{attempt_idx},{style_name},{is_tir},{answer},{answer_is_correct},"
                "{used_python},{python_error},{entropy},{verifier_verdict},{verifier_quality_score},{selected_final}\n".format(
                    **{k: r.get(k, "") for k in [
                        "problem_id", "domain", "attempt_idx", "style_name", "is_tir", "answer",
                        "answer_is_correct", "used_python", "python_error", "entropy",
                        "verifier_verdict", "verifier_quality_score", "selected_final"
                    ]}
                )
            )
