"""Addition problem generator.

Difficulty scaling:
  1 — single-digit + single-digit
  2 — two-digit  + single-digit
  3 — two-digit  + two-digit
  4 — three-digit + three-digit
  5 — three-operand chain (10-999 each)
"""

import random
from generators.models import Problem


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(difficulty: int, rng: random.Random) -> Problem:
    """Return a new addition Problem at the requested difficulty."""
    if difficulty == 5:
        return _three_operand(rng)

    a, b = _operands(difficulty, rng)
    answer = a + b
    prompt = f"What is {a} + {b}?"
    steps = _steps(a, b, answer)
    wrong = _common_errors(a, b, answer)

    return Problem(
        topic="Addition",
        difficulty=difficulty,
        prompt=prompt,
        correct_answer=str(answer),
        solution_steps=steps,
        common_wrong_answers=wrong,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

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
    """Build human-readable solution steps."""
    if a < 10 and b < 10:
        return [f"{a} + {b} = {answer}"]
    # Show vertical layout for multi-digit
    w = len(str(answer))
    return [
        f"  {a:>{w}}",
        f"+ {b:>{w}}",
        "-" * (w + 2),
        f"  {answer:>{w}}",
    ]


def _common_errors(a: int, b: int, answer: int) -> dict[str, str]:
    wrong: dict[str, str] = {}

    # "Forgot to carry" — sum each column mod 10, ignore the carry-out.
    no_carry = _no_carry_add(a, b)
    if no_carry != answer:
        wrong[str(no_carry)] = "forgot_to_carry"

    # Off by one (very common mental-math slip)
    if str(answer - 1) not in wrong and answer - 1 > 0:
        wrong[str(answer - 1)] = "off_by_one"

    return wrong


def _no_carry_add(a: int, b: int) -> int:
    """Add *a* and *b* digit-by-digit without propagating carries."""
    result = 0
    place = 1
    while a > 0 or b > 0:
        digit_sum = (a % 10) + (b % 10)
        result += (digit_sum % 10) * place
        a //= 10
        b //= 10
        place *= 10
    return result


def _three_operand(rng: random.Random) -> Problem:
    a = rng.randint(10, 999)
    b = rng.randint(10, 999)
    c = rng.randint(10, 999)
    answer = a + b + c

    prompt = f"What is {a} + {b} + {c}?"
    steps = [
        f"First, {a} + {b} = {a + b}",
        f"Then, {a + b} + {c} = {answer}",
    ]

    wrong: dict[str, str] = {}
    no_carry_ab = _no_carry_add(a, b)
    if no_carry_ab != a + b:
        wrong[str(no_carry_ab + c)] = "forgot_to_carry"

    return Problem(
        topic="Addition",
        difficulty=5,
        prompt=prompt,
        correct_answer=str(answer),
        solution_steps=steps,
        common_wrong_answers=wrong,
    )

