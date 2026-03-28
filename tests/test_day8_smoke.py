"""Day8 smoke tests — CLI solver mode (subscription auth via claude --print).

Tests cover:
  - create_solver(CLI) raises SolverConfigError when `claude` not in PATH
  - create_solver(CLI) succeeds when `claude` is available (mocked shutil.which)
  - CLI solver subprocess call and return value (mocked subprocess.run)
  - subprocess non-zero exit raises RuntimeError
  - subprocess TimeoutExpired propagates
  - VALID_MODES includes CLI
  - create_solver with unknown mode still raises ValueError
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from day1_minimal_baseline.solver import (
    CLI,
    LLM,
    PLACEHOLDER,
    VALID_MODES,
    SolverConfigError,
    create_solver,
)


SAMPLE_RECORD = {
    "id": "alg_001",
    "source": "2021 AIME I #5",
    "domain": "algebra",
    "difficulty": 1,
    "answer": "00041",
    "answer_raw": 41,
    "notes": "special arithmetic sequence",
}


# ---------------------------------------------------------------------------
# VALID_MODES completeness
# ---------------------------------------------------------------------------

def test_cli_in_valid_modes():
    assert CLI in VALID_MODES


def test_all_three_modes_present():
    assert set(VALID_MODES) == {PLACEHOLDER, LLM, CLI}


# ---------------------------------------------------------------------------
# create_solver(CLI) — missing claude CLI
# ---------------------------------------------------------------------------

def test_create_cli_solver_missing_claude_raises():
    """SolverConfigError when `claude` not found in PATH."""
    with patch("day1_minimal_baseline.solver.shutil.which", return_value=None):
        with pytest.raises(SolverConfigError, match="claude.*CLI not found"):
            create_solver(CLI)


# ---------------------------------------------------------------------------
# create_solver(CLI) — claude CLI present, mocked subprocess
# ---------------------------------------------------------------------------

def _make_mock_result(stdout="42", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.stderr = ""
    m.returncode = returncode
    return m


def test_create_cli_solver_returns_callable():
    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)
    assert callable(solver)


def test_cli_solver_returns_stripped_stdout():
    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)

    with patch("day1_minimal_baseline.solver.subprocess.run", return_value=_make_mock_result("  123  ")):
        result = solver(SAMPLE_RECORD)

    assert result == "123"


def test_cli_solver_passes_correct_command():
    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)

    mock_run = MagicMock(return_value=_make_mock_result("42"))
    with patch("day1_minimal_baseline.solver.subprocess.run", mock_run):
        solver(SAMPLE_RECORD)

    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "claude"
    assert "--print" in cmd
    assert "--output-format" in cmd
    assert "text" in cmd


def test_cli_solver_sends_source_in_prompt():
    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)

    mock_run = MagicMock(return_value=_make_mock_result("42"))
    with patch("day1_minimal_baseline.solver.subprocess.run", mock_run):
        solver(SAMPLE_RECORD)

    _, kwargs = mock_run.call_args
    prompt = kwargs["input"]
    assert SAMPLE_RECORD["source"] in prompt
    assert SAMPLE_RECORD["domain"] in prompt


def test_cli_solver_nonzero_exit_raises_runtime_error():
    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)

    bad = _make_mock_result("", returncode=1)
    bad.stderr = "some error"
    with patch("day1_minimal_baseline.solver.subprocess.run", return_value=bad):
        with pytest.raises(RuntimeError, match="exited 1"):
            solver(SAMPLE_RECORD)


def test_cli_solver_timeout_propagates():
    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)

    with patch(
        "day1_minimal_baseline.solver.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["claude"], timeout=200),
    ):
        with pytest.raises(subprocess.TimeoutExpired):
            solver(SAMPLE_RECORD)


# ---------------------------------------------------------------------------
# Backward compatibility — existing modes unaffected
# ---------------------------------------------------------------------------

def test_placeholder_mode_still_works():
    solver = create_solver(PLACEHOLDER)
    assert solver(SAMPLE_RECORD) == "00000"


def test_unknown_mode_still_raises_value_error():
    with pytest.raises(ValueError, match="Unknown solver mode"):
        create_solver("bogus")


# ---------------------------------------------------------------------------
# Pipeline integration — CLI solver via run_one_with_candidates (mocked)
# ---------------------------------------------------------------------------

def test_pipeline_accepts_cli_solver():
    from day1_minimal_baseline.pipeline import run_one_with_candidates

    with patch("day1_minimal_baseline.solver.shutil.which", return_value="/usr/bin/claude"):
        solver = create_solver(CLI)

    with patch("day1_minimal_baseline.solver.subprocess.run", return_value=_make_mock_result("41")):
        result = run_one_with_candidates(SAMPLE_RECORD, num_candidates=1, solver=solver)

    assert result["predicted"] == "00041"
    assert result["correct"] is True
