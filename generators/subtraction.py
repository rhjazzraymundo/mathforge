"""Subtraction problem generator.

Difficulty scaling:
  1 — single-digit - single-digit  (result > 0)
  2 — two-digit  - single-digit
  3 — two-digit  - two-digit
  4 — three-digit - three-digit
  5 — three-operand chain  a - b - c  (result >= 0)
"""

import random
from generators.models import Problem


def generate(difficulty: int, rng: random.Random) -> Problem:
    if difficulty == 5:
        return _three_operand(rng)

    a, b = _operands(difficulty, rng)
    # Guarantee a > b so the answer is positive.
    if a < b:
        a, b = b, a
    if a == b:
        a += 1  # nudge to avoid trivial 0 answers

    answer = a - b
    prompt = f"What is {a} - {b}?"
    steps = _steps(a, b, answer)
    wrong = _common_errors(a, b, answer)

    return Problem(
        topic="Subtraction",
        difficulty=difficulty,
        prompt=prompt,
        correct_answer=str(answer),
        solution_steps=steps,
        common_wrong_answers=wrong,
    )


_RANGES: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {
    1: ((1, 9), (1, 9)),
    2: ((10, 99), (1, 9)),
    3: ((10, 99), (10, 99)),
    4: ((100, 999), (100, 999)),
}


def _operands(difficulty: int, rng: random.Random) -> tuple[int, int]:
    if difficulty not in _RANGES:
        raise ValueError(f"Difficulty must be 1-5, got {difficulty}")
    (lo_a, hi_a), (lo_b, hi_b) = _RANGES[difficulty]
    return rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)


def _steps(a: int, b: int, answer: int) -> list[str]:
    if a < 10:
        return [f"{a} - {b} = {answer}"]
    w = len(str(a))
    return [
        f"  {a:>{w}}",
        f"- {b:>{w}}",
        "-" * (w + 2),
        f"  {answer:>{w}}",
    ]


def _common_errors(a: int, b: int, answer: int) -> dict[str, str]:
    wrong: dict[str, str] = {}

    # "Forgot to borrow" — in each column, subtract smaller from larger.
    no_borrow = _no_borrow_sub(a, b)
    if no_borrow != answer:
        wrong[str(no_borrow)] = "forgot_to_borrow"

    # Off by one
    if str(answer + 1) not in wrong:
        wrong[str(answer + 1)] = "off_by_one"

    return wrong


def _no_borrow_sub(a: int, b: int) -> int:
    """Subtract digit-by-digit, taking abs() per column (no borrowing)."""
    result = 0
    place = 1
    while a > 0 or b > 0:
        result += abs((a % 10) - (b % 10)) * place
        a //= 10
        b //= 10
        place *= 10
    return result


def _three_operand(rng: random.Random) -> Problem:
    """a - b - c where a > b + c."""
    a = rng.randint(100, 999)
    b = rng.randint(1, a // 3)
    c = rng.randint(1, a // 3)
    answer = a - b - c

    prompt = f"What is {a} - {b} - {c}?"
    steps = [
        f"First, {a} - {b} = {a - b}",
        f"Then, {a - b} - {c} = {answer}",
    ]

    wrong: dict[str, str] = {}
    # Common: accidentally added c instead of subtracting
    bad = a - b + c
    if bad != answer:
        wrong[str(bad)] = "sign_error"

    return Problem(
        topic="Subtraction",
        difficulty=5,
        prompt=prompt,
        correct_answer=str(answer),
        solution_steps=steps,
        common_wrong_answers=wrong,
    )

