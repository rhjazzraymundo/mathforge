"""Division problem generator.

Difficulty scaling:
  1 — exact, divisor 2-9, quotient 1-9       (tables facts)
  2 — exact, divisor 2-12, quotient 2-12
  3 — with remainder, dividend <= ~120
  4 — exact, divisor 2-20, quotient 10-50
  5 — with remainder, larger numbers

Remainder answers use the format "Q r R"  (e.g. "7 r 3").
"""

import random
from generators.models import Problem


def generate(difficulty: int, rng: random.Random) -> Problem:
    if difficulty in (1, 2, 4):
        return _exact(difficulty, rng)
    if difficulty in (3, 5):
        return _remainder(difficulty, rng)
    raise ValueError(f"Difficulty must be 1-5, got {difficulty}")


# ---------------------------------------------------------------------------
# Exact division
# ---------------------------------------------------------------------------

def _exact(difficulty: int, rng: random.Random) -> Problem:
    # Build dividend from divisor * quotient so it's always exact.
    if difficulty == 1:
        divisor = rng.randint(2, 9)
        quotient = rng.randint(1, 9)
    elif difficulty == 2:
        divisor = rng.randint(2, 12)
        quotient = rng.randint(2, 12)
    else:  # 4
        divisor = rng.randint(2, 20)
        quotient = rng.randint(10, 50)

    dividend = divisor * quotient

    prompt = f"What is {dividend} / {divisor}?"
    steps = [
        f"Think: {divisor} x ? = {dividend}",
        f"{divisor} x {quotient} = {dividend}",
        f"So {dividend} / {divisor} = {quotient}",
    ]

    wrong: dict[str, str] = {}
    # Off by one
    if quotient - 1 > 0:
        wrong[str(quotient - 1)] = "off_by_one"
    wrong[str(quotient + 1)] = "off_by_one"
    # Flipped operands — student divides the wrong way around
    if divisor != quotient and divisor != dividend:
        wrong[str(divisor)] = "flipped_division"

    return Problem(
        topic="Division",
        difficulty=difficulty,
        prompt=prompt,
        correct_answer=str(quotient),
        solution_steps=steps,
        common_wrong_answers=wrong,
    )


# ---------------------------------------------------------------------------
# Division with remainder
# ---------------------------------------------------------------------------

def _remainder(difficulty: int, rng: random.Random) -> Problem:
    if difficulty == 3:
        divisor = rng.randint(2, 9)
        quotient = rng.randint(1, 12)
    else:  # 5
        divisor = rng.randint(2, 50)
        quotient = rng.randint(10, 50)

    remainder = rng.randint(1, divisor - 1)
    dividend = divisor * quotient + remainder
    answer_str = f"{quotient} r {remainder}"

    prompt = f"What is {dividend} / {divisor}? (Give answer as Q r R)"
    steps = [
        f"{divisor} x {quotient} = {divisor * quotient}",
        f"{dividend} - {divisor * quotient} = {remainder}",
        f"So {dividend} / {divisor} = {quotient} remainder {remainder}",
    ]

    wrong: dict[str, str] = {}
    # Forgot the remainder entirely
    wrong[str(quotient)] = "forgot_remainder"
    # Off by one on the quotient
    alt_q = quotient + 1
    alt_r = dividend - divisor * alt_q
    if 0 <= alt_r < divisor:
        wrong[f"{alt_q} r {alt_r}"] = "off_by_one"

    return Problem(
        topic="Division",
        difficulty=difficulty,
        prompt=prompt,
        correct_answer=answer_str,
        solution_steps=steps,
        common_wrong_answers=wrong,
    )

