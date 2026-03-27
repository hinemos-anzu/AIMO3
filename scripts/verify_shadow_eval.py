#!/usr/bin/env python3
"""Verification script for shadow_eval_v1.0 dataset integrity.

Checks:
  1. All records have answer_raw in [0, 99999]
  2. answer == str(answer_raw).zfill(5) for every record (transform consistency)
  3. Total record count == 32
  4. Domain distribution: algebra/combinatorics/geometry/number_theory == 8 each
  5. Difficulty distribution: 1 == 16, 2 == 16

Exits with code 0 and prints PASS on success.
Exits with code 1 and prints FAIL with details on any violation.
No silent fallback.
"""

import json
import os
import sys

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shadow_eval.jsonl")

EXPECTED_TOTAL = 32
EXPECTED_DOMAINS = {"algebra": 8, "combinatorics": 8, "geometry": 8, "number_theory": 8}
EXPECTED_DIFFICULTIES = {1: 16, 2: 16}
ANSWER_RAW_MIN = 0
ANSWER_RAW_MAX = 99999


def verify_transform_consistency(path: str) -> list[str]:
    """Run all v1.0 integrity checks.

    Returns a list of failure messages.
    Empty list means PASS.
    Raises FileNotFoundError if the dataset is missing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path!r}")

    records = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                return [f"Line {lineno}: invalid JSON — {exc}"]

    failures: list[str] = []

    # 1. Total count
    if len(records) != EXPECTED_TOTAL:
        failures.append(
            f"Total record count: expected {EXPECTED_TOTAL}, got {len(records)}"
        )

    # 2. answer_raw range + transform consistency
    for rec in records:
        rid = rec.get("id", "?")
        raw = rec.get("answer_raw")
        answer = rec.get("answer")

        if raw is None:
            failures.append(f"{rid}: missing answer_raw")
            continue
        if not isinstance(raw, int):
            failures.append(f"{rid}: answer_raw is not int: {raw!r}")
            continue
        if not (ANSWER_RAW_MIN <= raw <= ANSWER_RAW_MAX):
            failures.append(
                f"{rid}: answer_raw out of range [{ANSWER_RAW_MIN}, {ANSWER_RAW_MAX}]: {raw}"
            )
        expected_answer = str(raw).zfill(5)
        if answer != expected_answer:
            failures.append(
                f"{rid}: transform mismatch — answer={answer!r}, "
                f"expected zfill(5)({raw})={expected_answer!r}"
            )

    # 3. Domain distribution
    from collections import Counter
    domain_counts = dict(Counter(r.get("domain") for r in records))
    for domain, expected_count in EXPECTED_DOMAINS.items():
        actual = domain_counts.get(domain, 0)
        if actual != expected_count:
            failures.append(
                f"Domain '{domain}': expected {expected_count} records, got {actual}"
            )

    # 4. Difficulty distribution
    diff_counts = dict(Counter(r.get("difficulty") for r in records))
    for level, expected_count in EXPECTED_DIFFICULTIES.items():
        actual = diff_counts.get(level, 0)
        if actual != expected_count:
            failures.append(
                f"Difficulty {level}: expected {expected_count} records, got {actual}"
            )

    return failures


def main() -> int:
    print(f"Verifying: {DATA_PATH}")
    failures = verify_transform_consistency(DATA_PATH)

    if not failures:
        print(f"Checked {EXPECTED_TOTAL} records.")
        print("PASS")
        return 0

    print(f"FAIL — {len(failures)} violation(s):")
    for msg in failures:
        print(f"  - {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
