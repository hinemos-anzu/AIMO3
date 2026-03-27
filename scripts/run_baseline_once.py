#!/usr/bin/env python3
"""Run the Day1 baseline on the first record of shadow_eval.jsonl.

Usage:
    python scripts/run_baseline_once.py

Exits with code 0 on success, 1 on any error.
"""

import os
import sys

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.io import load_jsonl
from day1_minimal_baseline.pipeline import run_one

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")


def main() -> int:
    records = load_jsonl(DATA_PATH)
    first = records[0]
    result = run_one(first)

    print("=== Day1 baseline — first record ===")
    for key, val in result.items():
        print(f"  {key}: {val}")

    print()
    if result["correct"]:
        print("CORRECT")
    else:
        print(f"WRONG  predicted={result['predicted']}  expected={result['expected']}")

    # Day1 uses a placeholder solver, so WRONG is expected — not a failure.
    return 0


if __name__ == "__main__":
    sys.exit(main())
