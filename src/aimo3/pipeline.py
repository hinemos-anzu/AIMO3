from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaselineConfig:
    """Day1 baseline configuration.

    TODO(day2): split module-wise configs once generator/executor/verifier are replaced.
    """

    answer_digits: int = 5


class SimpleGenerator:
    def generate(self, problem: str) -> str:
        # Minimal, deterministic baseline prompt transform.
        return problem.strip()


class SimpleExecutor:
    def execute(self, generated_text: str) -> int:
        # Minimal executor: hash-like deterministic integer derived from text.
        return sum(ord(ch) for ch in generated_text)


class SimpleVerifierSelector:
    def select(self, executor_value: int, digits: int) -> str:
        mod = 10**digits
        return f"{executor_value % mod:0{digits}d}"


def solve_once(problem: str, cfg: BaselineConfig | None = None) -> str:
    config = cfg or BaselineConfig()
    generator = SimpleGenerator()
    executor = SimpleExecutor()
    verifier = SimpleVerifierSelector()

    candidate = generator.generate(problem)
    value = executor.execute(candidate)
    return verifier.select(value, config.answer_digits)
