#!/usr/bin/env python3
"""Run the baseline on the first record of shadow_eval.jsonl.

Usage:
    python scripts/run_baseline_once.py
    python scripts/run_baseline_once.py --solver-mode llm
    python scripts/run_baseline_once.py --solver-mode llm --model claude-haiku-4-5-20251001

--solver-mode placeholder (default): no API key required.
--solver-mode llm: requires ANTHROPIC_API_KEY environment variable.

Exits with code 0 on success, 1 on any error.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import run_one, run_one_with_candidates
from day1_minimal_baseline.solver import LLM, PLACEHOLDER, SolverConfigError, create_solver

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description="AIMO3 single-record baseline runner")
    parser.add_argument(
        "--solver-mode",
        default=PLACEHOLDER,
        choices=[PLACEHOLDER, LLM],
        help=f"Solver mode: '{PLACEHOLDER}' (default, no API key) or '{LLM}'",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Claude model ID for LLM solver (ignored in placeholder mode)",
    )
    args = parser.parse_args()

    records = load_jsonl(DATA_PATH)
    first = records[0]

    if args.solver_mode == LLM:
        try:
            solver_fn = create_solver(LLM, model=args.model)
        except SolverConfigError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        result = run_one_with_candidates(first, num_candidates=1, solver=solver_fn)
    else:
        result = run_one(first)

    print(f"=== baseline — first record [solver={args.solver_mode}] ===")
    for key, val in result.items():
        if key not in ("candidates", "exec_errors"):
            print(f"  {key}: {val}")

    print()
    if result["correct"]:
        print("CORRECT")
    else:
        print(f"WRONG  predicted={result['predicted']}  expected={result['expected']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
