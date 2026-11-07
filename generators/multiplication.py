"""Multiplication problem generator.

Difficulty scaling:
  1 — single × single        (2-9)
  2 — two-digit × single     (10-99 × 2-9)
  3 — two-digit × two-digit  (10-99 × 10-99)
  4 — three-digit × single   (100-999 × 2-9)
  5 — three-digit × two-digit(100-999 × 10-99)
"""

import random
from generators.models import Problem


def generate(difficulty: int, rng: random.Random) -> Problem:
    a, b = _operands(difficulty, rng)
    answer = a * b
    prompt = f"What is {a} x {b}?"
    steps = _steps(a, b, answer, difficulty)
    wrong = _common_errors(a, b, answer)

    return Problem(
        topic="Multiplication",
        difficulty=difficulty,
        prompt=prompt,
        correct_answer=str(answer),
        solution_steps=steps,
        common_wrong_answers=wrong,
    )


_RANGES: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {
    1: ((2, 9), (2, 9)),
    2: ((10, 99), (2, 9)),
    3: ((10, 99), (10, 99)),
    4: ((100, 999), (2, 9)),
    5: ((100, 999), (10, 99)),
}


def _operands(difficulty: int, rng: random.Random) -> tuple[int, int]:
    if difficulty not in _RANGES:
        raise ValueError(f"Difficulty must be 1-5, got {difficulty}")
    (lo_a, hi_a), (lo_b, hi_b) = _RANGES[difficulty]
    return rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)


def _steps(a: int, b: int, answer: int, difficulty: int) -> list[str]:
    if difficulty <= 2:
        return [f"{a} x {b} = {answer}"]
    # Distributive property for larger multiplications
    if b >= 10:
        tens = (b // 10) * 10
        ones = b % 10
        part1 = a * tens
        part2 = a * ones
        return [
            f"Break {b} into {tens} + {ones}",
            f"{a} x {tens} = {part1}",
            f"{a} x {ones} = {part2}",
            f"{part1} + {part2} = {answer}",
        ]
    return [f"{a} x {b} = {answer}"]


def _common_errors(a: int, b: int, answer: int) -> dict[str, str]:
    wrong: dict[str, str] = {}

    # Confused with addition
    added = a + b
    if added != answer:
        wrong[str(added)] = "added_instead"

    # Multiplied by (b-1) instead of b
    off = a * (b - 1)
    if off != answer and off > 0 and str(off) not in wrong:
        wrong[str(off)] = "off_by_one_factor"

    return wrong

