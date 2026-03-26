#!/usr/bin/env python3
"""Preflight checks for AIMO3 exp_001 dataset integrity (CHECK-01)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

ALLOWED_DOMAINS = {"algebra", "combinatorics", "geometry", "number_theory"}
ALLOWED_DIFFICULTIES = {"1", "2"}
BANNED_TOKENS = {"toy", "mock", "dummy", "test"}


def print_result(label: str, status: str, detail: str) -> None:
    print(f"[{status}] {label}: {detail}")


def main() -> int:
    path = Path("data/shadow_eval.jsonl")
    if not path.exists():
        print_result(
            "CHECK-01",
            "FAIL",
            "data/shadow_eval.jsonl が存在しません。real用評価データを配置してください。",
        )
        return 1

    problems = []
    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                print_result("CHECK-01", "FAIL", f"{path} の {i} 行目が空行です。JSONL は空行不可です。")
                return 1
            try:
                problems.append(json.loads(line))
            except json.JSONDecodeError as e:
                print_result("CHECK-01", "FAIL", f"{path} の {i} 行目が不正なJSONです: {e}")
                return 1

    domains = Counter(p.get("domain", "MISSING") for p in problems)
    difficulties = Counter(str(p.get("difficulty", "MISSING")) for p in problems)

    ids = [p.get("problem_id", p.get("id")) for p in problems]
    missing_ids = sum(x is None for x in ids)
    duplicate_count = len(ids) - len(set(ids))

    bad_domain = [p for p in problems if p.get("domain") not in ALLOWED_DOMAINS]
    bad_diff = [p for p in problems if str(p.get("difficulty")) not in ALLOWED_DIFFICULTIES]

    bad_text = []
    for p in problems:
        serialized = json.dumps(p, ensure_ascii=False).lower()
        if any(t in serialized for t in BANNED_TOKENS):
            bad_text.append(p.get("problem_id", p.get("id", "MISSING")))

    print(f"行数: {len(problems)}")
    print(f"domain内訳: {dict(domains)}")
    print(f"difficulty内訳: {dict(difficulties)}")
    print(f"ID欠損数: {missing_ids}")
    print(f"ID重複数: {duplicate_count}")
    print(f"bad_domain_count: {len(bad_domain)}")
    print(f"bad_diff_count: {len(bad_diff)}")
    print(f"toy/mock文字列件数: {len(bad_text)}")
    print(f"先頭3件: {ids[:3]}")
    print(f"末尾3件: {ids[-3:]}")

    failures = []
    if missing_ids:
        failures.append(f"ID欠損 {missing_ids} 件")
    if duplicate_count:
        failures.append(f"ID重複 {duplicate_count} 件")
    if bad_domain:
        failures.append(f"不正domain {len(bad_domain)} 件")
    if bad_diff:
        failures.append(f"不正difficulty {len(bad_diff)} 件")
    if bad_text:
        failures.append(f"toy/mock/dummy/test 文字列 {len(bad_text)} 件")

    if failures:
        print_result("CHECK-01", "FAIL", "; ".join(failures))
        return 1

    print_result("CHECK-01", "PASS", "shadow_eval.jsonl は baseline 実行前条件を満たしています。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
