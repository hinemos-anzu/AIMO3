#!/usr/bin/env python3
"""Run the Day2 batch baseline over shadow_eval.jsonl.

Usage:
    python scripts/run_baseline_batch.py
    python scripts/run_baseline_batch.py --limit 3

Exits with code 0 on success, 1 on any error.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import run_batch

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description="AIMO3 batch baseline runner")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N records (default: all)",
    )
    args = parser.parse_args()

    records = load_jsonl(DATA_PATH)
    batch = run_batch(records, limit=args.limit)

    print("=== Day2 batch baseline ===")
    print(f"  total   : {batch['total']}")
    print(f"  correct : {batch['correct']}")
    print(f"  accuracy: {batch['accuracy']:.4f}")
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
