"""JSONL loader for shadow_eval dataset.

Raises explicit errors on every failure case — no silent fallback.
"""

import json
import os
from typing import Any


REQUIRED_FIELDS = {"id", "answer", "domain", "difficulty"}


def load_jsonl(path: str) -> list[dict[str, Any]]:
    """Load all records from a JSONL file.

    Raises:
        FileNotFoundError: path does not exist.
        ValueError: file is empty, a line is not valid JSON,
                    or a required field is missing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path!r}")

    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {lineno}: {exc}") from exc

            missing = REQUIRED_FIELDS - record.keys()
            if missing:
                raise ValueError(
                    f"Line {lineno} missing required fields: {sorted(missing)}"
                )

            records.append(record)

    if not records:
        raise ValueError(f"Dataset is empty: {path!r}")

    return records
