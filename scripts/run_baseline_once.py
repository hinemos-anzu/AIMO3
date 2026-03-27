#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aimo3.pipeline import BaselineConfig, solve_once


def read_first_problem(dataset_path: Path) -> tuple[str, str]:
    with dataset_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            return str(obj["id"]), str(obj["problem"])
    raise ValueError(f"No valid rows found in {dataset_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Day1 baseline once on shadow eval.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT / "data" / "shadow_eval.jsonl",
        help="JSONL path for shadow eval dataset",
    )
    args = parser.parse_args()

    qid, problem = read_first_problem(args.dataset)
    answer = solve_once(problem, BaselineConfig(answer_digits=5))

    result = {"id": qid, "answer": answer, "answer_digits": 5}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
