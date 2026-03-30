#!/usr/bin/env python3
"""Run the Day5 Run3 batch baseline over shadow_eval.jsonl.

Usage:
    python scripts/run_baseline_batch.py                           # N=1, retry=0
    python scripts/run_baseline_batch.py --limit 3
    python scripts/run_baseline_batch.py --max-retries 1           # Run2 path
    python scripts/run_baseline_batch.py --num-candidates 16       # Run3 N=16
    python scripts/run_baseline_batch.py --num-candidates 32       # Run3 N=32
    python scripts/run_baseline_batch.py --num-candidates 64       # Run3 N=64
    python scripts/run_baseline_batch.py --num-candidates 16 --max-retries 1

Routing:
    num_candidates=1  AND max_retries=0 → run_batch()            (backward compat)
    num_candidates=1  AND max_retries>0 → run_batch_with_retry() (Run2)
    num_candidates>1                    → run_batch_with_candidates() (Run3)

Exits with code 0 on success, 1 on any error.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import (
    format_summary,
    run_batch,
    run_batch_with_candidates,
    run_batch_with_retry,
)
from day1_minimal_baseline.solver import CLI, LLM, PLACEHOLDER, SolverConfigError, create_solver

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


def _print_breakdown(label: str, bd: dict) -> None:
    print(f"  {label}:")
    for key, stats in bd.items():
        print(
            f"    {str(key):<16}  total={stats['total']:>3}  "
            f"correct={stats['correct']:>3}  acc={stats['accuracy']:.4f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="AIMO3 batch baseline runner")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N records (default: all)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=0,
        metavar="R",
        help="Per-problem retry limit on exec errors: 0=no retry (default), 1, 2, ...",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=250.0,
        metavar="T",
        help="Per-problem wall-clock time limit in seconds (default: 250)",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=1,
        metavar="N",
        help="Number of solver candidates per problem: 1 (default), 16, 32, 64, ...",
    )
    parser.add_argument(
        "--solver-mode",
        default=PLACEHOLDER,
        choices=[PLACEHOLDER, LLM, CLI],
        help=(
            f"'{PLACEHOLDER}' (default), "
            f"'{LLM}' (requires ANTHROPIC_API_KEY), or "
            f"'{CLI}' (claude --print, subscription auth)"
        ),
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Claude model ID (used only when --solver-mode llm)",
    )
    parser.add_argument(
        "--effort",
        default="low",
        choices=["low", "medium", "high", "max"],
        help="claude --effort level for cli mode (default: low)",
    )
    args = parser.parse_args()

    # Resolve solver
    if args.solver_mode in (LLM, CLI):
        try:
            solver_fn = create_solver(args.solver_mode, model=args.model, effort=args.effort)
        except SolverConfigError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    else:
        solver_fn = None  # None → solve_placeholder inside pipeline

    records = load_jsonl(DATA_PATH)

    if args.num_candidates > 1 or args.solver_mode in (LLM, CLI):
        batch = run_batch_with_candidates(
            records,
            limit=args.limit,
            num_candidates=args.num_candidates,
            max_retries=args.max_retries,
            timeout_sec=args.timeout_sec,
            solver=solver_fn,
        )
    elif args.max_retries > 0:
        batch = run_batch_with_retry(
            records,
            limit=args.limit,
            max_retries=args.max_retries,
            timeout_sec=args.timeout_sec,
            solver=solver_fn,
        )
    else:
        batch = run_batch(records, limit=args.limit)

    summary = format_summary(batch)
    comp = summary["answer_5digit_compliance"]

    print("=== Day5 Run3 batch baseline — summary ===")
    print(f"  total              : {summary['total']}")
    print(f"  correct            : {summary['correct']}")
    print(f"  accuracy           : {summary['accuracy']:.4f}")
    print(
        f"  5digit_compliance  : {comp['compliant']}/{comp['total']}"
        f"  ({comp['rate']:.4f})"
    )

    if "parse_stats" in summary:
        ps = summary["parse_stats"]
        print()
        print("  parse stats:")
        print(f"    parse_success_count : {ps['parse_success_count']}")
        print(f"    parse_failure_count : {ps['parse_failure_count']}")

    if "candidate_stats" in summary:
        cs = summary["candidate_stats"]
        print()
        print("  candidate stats:")
        print(f"    num_candidates_setting  : {cs['num_candidates_setting']}")
        print(f"    avg_candidate_diversity : {cs['avg_candidate_diversity']:.6f}")

    if "retry_stats" in summary:
        rs = summary["retry_stats"]
        print()
        print("  retry stats:")
        print(f"    max_retries_setting : {rs['max_retries_setting']}")
        print(f"    timeout_sec_setting : {rs['timeout_sec_setting']}")
        print(f"    retry_count_used    : {rs['retry_count_used']}")
        print(f"    exec_error_count    : {rs['exec_error_count']}")
        print(f"    avg_runtime_sec     : {rs['avg_runtime_sec']:.4f}")
        print(f"    max_runtime_sec     : {rs['max_runtime_sec']:.4f}")

    if "breakdown_domain" in summary:
        print()
        _print_breakdown("domain breakdown", summary["breakdown_domain"])

    if "breakdown_difficulty" in summary:
        print()
        _print_breakdown("difficulty breakdown", summary["breakdown_difficulty"])

    print()
    print(f"{'id':<12} {'domain':<14} {'diff':>4}  {'pred':>5}  {'gold':>5}  ok?")
    print("-" * 58)
    for r in batch["results"]:
        ok = "OK" if r["correct"] else "--"
        print(
            f"{r['id']:<12} {r['domain']:<14} {r['difficulty']:>4}  "
            f"{r['predicted']:>5}  {r['expected']:>5}  {ok}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
