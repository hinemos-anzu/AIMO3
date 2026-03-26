import json
import subprocess
import sys


def test_run_baseline_once_outputs_5_digits():
    proc = subprocess.run(
        [sys.executable, "scripts/run_baseline_once.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout.strip())
    assert out["id"]
    assert isinstance(out["answer"], str)
    assert len(out["answer"]) == 5
    assert out["answer"].isdigit()
