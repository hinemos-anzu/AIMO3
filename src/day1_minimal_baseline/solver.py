"""Solver adapter for Day6+.

Provides two modes:
  "placeholder"  — always returns "00000" (Day1-Day5 baseline behaviour).
  "llm"          — calls the Anthropic Claude API with problem metadata.

Usage:
    from day1_minimal_baseline.solver import create_solver, PLACEHOLDER, LLM

    solver = create_solver(PLACEHOLDER)          # no API key needed
    solver = create_solver(LLM, model="...")     # requires ANTHROPIC_API_KEY

Design rules (same as pipeline.py):
  - Silent fallback is forbidden.
  - SolverConfigError is raised explicitly when the environment is
    misconfigured (missing API key, missing package).
  - The solver function returns a raw string; callers use format_answer()
    to normalise it to a 5-digit string.
"""

import os
from typing import Any, Callable

PLACEHOLDER = "placeholder"
LLM = "llm"

VALID_MODES = (PLACEHOLDER, LLM)


class SolverConfigError(ValueError):
    """Raised when a solver cannot be initialised due to missing config.

    Example: ANTHROPIC_API_KEY is not set when mode="llm" is requested.
    """


def _make_placeholder_solver() -> Callable[[dict[str, Any]], str]:
    """Return a solver that always yields '00000'."""
    def solve(record: dict[str, Any]) -> str:  # noqa: ARG001
        return "00000"
    return solve


def _make_llm_solver(model: str = "claude-haiku-4-5-20251001") -> Callable[[dict[str, Any]], str]:
    """Return a solver that calls the Anthropic Claude API.

    The solver constructs a minimal prompt from problem metadata
    (source, domain, difficulty, notes) and asks Claude for a numeric answer.
    No full problem text is available in shadow_eval_v1.0, so accuracy
    will be limited until problem text is added to the dataset.

    Raises:
        ImportError:       anthropic package is not installed.
        SolverConfigError: ANTHROPIC_API_KEY env var is not set.
    """
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required for LLM solver mode.\n"
            "Install it with:  pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SolverConfigError(
            "ANTHROPIC_API_KEY environment variable is not set.\n"
            "LLM solver requires a valid Anthropic API key.\n"
            "Set the key:  export ANTHROPIC_API_KEY=sk-...\n"
            "Or run in placeholder mode:  --solver-mode placeholder"
        )

    client = anthropic.Anthropic(api_key=api_key)

    def solve(record: dict[str, Any]) -> str:
        """Call Claude with problem metadata and return raw answer text.

        The caller (pipeline) is responsible for calling format_answer()
        to normalise the output to a 5-digit string.
        """
        notes = record.get("notes", "")
        prompt = (
            "You are solving an AIME (American Invitational Mathematics "
            "Examination) competition problem.\n\n"
            f"Problem source: {record['source']}\n"
            f"Mathematical domain: {record['domain']}\n"
            f"Difficulty level: {record['difficulty']} "
            "(1 = easier, 2 = harder within AIME)\n"
            f"Problem topic hint: {notes}\n\n"
            "AIME answers are non-negative integers between 0 and 999.\n"
            "Reply with ONLY the integer answer — no explanation, "
            "no units, just the number.\n"
            "Example reply: 42"
        )
        response = client.messages.create(
            model=model,
            max_tokens=16,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    return solve


def create_solver(
    mode: str = PLACEHOLDER,
    model: str = "claude-haiku-4-5-20251001",
) -> Callable[[dict[str, Any]], str]:
    """Create and return a solver callable for the given mode.

    Args:
        mode:  "placeholder" (default) or "llm".
        model: Claude model ID used when mode="llm".
               Ignored in placeholder mode.

    Returns:
        A callable: (record: dict) -> str (raw answer, not yet normalised).

    Raises:
        ValueError:        unknown mode string.
        SolverConfigError: mode="llm" but ANTHROPIC_API_KEY is not set.
        ImportError:       mode="llm" but anthropic package is missing.
    """
    if mode == PLACEHOLDER:
        return _make_placeholder_solver()
    if mode == LLM:
        return _make_llm_solver(model=model)
    raise ValueError(
        f"Unknown solver mode: {mode!r}. "
        f"Valid modes: {VALID_MODES}"
    )
