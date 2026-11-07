"""Fraction problem generator.

Difficulty scaling:
  1 — addition, same denominator
  2 — addition, one denominator divides the other
  3 — addition, any denominators (need LCD)
  4 — subtraction of fractions
  5 — multiplication of fractions

Answers are always fully simplified:  "3/4", "1", "5/2", etc.
The module is named fractions_gen to avoid shadowing Python's
built-in fractions module.
"""

import math
import random
from generators.models import Problem


def generate(difficulty: int, rng: random.Random) -> Problem:
    dispatch = {1: _same_denom_add, 2: _related_denom_add,
                3: _any_denom_add, 4: _subtract, 5: _multiply}
    if difficulty not in dispatch:
        raise ValueError(f"Difficulty must be 1-5, got {difficulty}")
    return dispatch[difficulty](rng)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simplify(num: int, den: int) -> tuple[int, int]:
    """Reduce to lowest terms; sign lives in the numerator."""
    if den < 0:
        num, den = -num, -den
    if num == 0:
        return 0, 1
    g = math.gcd(abs(num), den)
    return num // g, den // g


def _fmt(num: int, den: int) -> str:
    """Simplified fraction string, or plain integer when denominator is 1."""
    sn, sd = _simplify(num, den)
    return str(sn) if sd == 1 else f"{sn}/{sd}"


def _lcd(d1: int, d2: int) -> int:
    return d1 * d2 // math.gcd(d1, d2)


# ---------------------------------------------------------------------------
# Generators by difficulty
# ---------------------------------------------------------------------------

def _same_denom_add(rng: random.Random) -> Problem:
    den = rng.randint(2, 8)
    a = rng.randint(1, den - 1)
    b = rng.randint(1, den - 1)

    res_num = a + b
    answer = _fmt(res_num, den)
    sn, sd = _simplify(res_num, den)

    prompt = f"What is {a}/{den} + {b}/{den}? (Simplify your answer)"
    steps = [
        f"Same denominator, add numerators: {a} + {b} = {res_num}",
        f"Result: {res_num}/{den}",
    ]
    if (sn, sd) != (res_num, den):
        steps.append(f"Simplify: {res_num}/{den} = {_fmt(res_num, den)}")

    wrong = _addition_errors(a, b, den, den, answer, res_num, den)
    return Problem(topic="Fractions", difficulty=1, prompt=prompt,
                   correct_answer=answer, solution_steps=steps,
                   common_wrong_answers=wrong)


def _related_denom_add(rng: random.Random) -> Problem:
    small = rng.randint(2, 6)
    mult = rng.randint(2, 4)
    big = small * mult

    a = rng.randint(1, small - 1)
    b = rng.randint(1, big - 1)

    a_conv = a * mult
    res_num = a_conv + b

    answer = _fmt(res_num, big)
    sn, sd = _simplify(res_num, big)

    prompt = f"What is {a}/{small} + {b}/{big}? (Simplify your answer)"
    steps = [
        f"Convert {a}/{small} to {a_conv}/{big} (multiply top and bottom by {mult})",
        f"Add: {a_conv}/{big} + {b}/{big} = {res_num}/{big}",
    ]
    if (sn, sd) != (res_num, big):
        steps.append(f"Simplify: {res_num}/{big} = {_fmt(res_num, big)}")

    wrong = _addition_errors(a, b, small, big, answer, res_num, big)
    return Problem(topic="Fractions", difficulty=2, prompt=prompt,
                   correct_answer=answer, solution_steps=steps,
                   common_wrong_answers=wrong)


def _any_denom_add(rng: random.Random) -> Problem:
    d1 = rng.randint(2, 9)
    d2 = rng.randint(2, 9)
    while d2 == d1:
        d2 = rng.randint(2, 9)

    a = rng.randint(1, d1 - 1)
    b = rng.randint(1, d2 - 1)

    common = _lcd(d1, d2)
    a_conv = a * (common // d1)
    b_conv = b * (common // d2)
    res_num = a_conv + b_conv

    answer = _fmt(res_num, common)
    sn, sd = _simplify(res_num, common)

    prompt = f"What is {a}/{d1} + {b}/{d2}? (Simplify your answer)"
    steps = [
        f"LCD of {d1} and {d2} is {common}",
        f"Convert: {a}/{d1} = {a_conv}/{common}",
        f"Convert: {b}/{d2} = {b_conv}/{common}",
        f"Add: {a_conv}/{common} + {b_conv}/{common} = {res_num}/{common}",
    ]
    if (sn, sd) != (res_num, common):
        steps.append(f"Simplify: {res_num}/{common} = {_fmt(res_num, common)}")

    wrong = _addition_errors(a, b, d1, d2, answer, res_num, common)
    return Problem(topic="Fractions", difficulty=3, prompt=prompt,
                   correct_answer=answer, solution_steps=steps,
                   common_wrong_answers=wrong)


def _subtract(rng: random.Random) -> Problem:
    d1 = rng.randint(2, 9)
    d2 = rng.randint(2, 9)
    while d2 == d1:
        d2 = rng.randint(2, 9)

    a = rng.randint(1, d1 - 1)
    b = rng.randint(1, d2 - 1)

    common = _lcd(d1, d2)
    a_conv = a * (common // d1)
    b_conv = b * (common // d2)

    # Ensure positive result by putting the larger fraction first
    if a_conv < b_conv:
        a, d1, b, d2 = b, d2, a, d1
        a_conv, b_conv = b_conv, a_conv
    if a_conv == b_conv:          # equal fractions → bump numerator
        a += 1
        a_conv = a * (common // d1)

    res_num = a_conv - b_conv
    answer = _fmt(res_num, common)
    sn, sd = _simplify(res_num, common)

    prompt = f"What is {a}/{d1} - {b}/{d2}? (Simplify your answer)"
    steps = [
        f"LCD of {d1} and {d2} is {common}",
        f"Convert: {a}/{d1} = {a_conv}/{common}",
        f"Convert: {b}/{d2} = {b_conv}/{common}",
        f"Subtract: {a_conv}/{common} - {b_conv}/{common} = {res_num}/{common}",
    ]
    if (sn, sd) != (res_num, common):
        steps.append(f"Simplify: {res_num}/{common} = {_fmt(res_num, common)}")

    wrong: dict[str, str] = {}
    # Accidentally added
    add_answer = _fmt(a_conv + b_conv, common)
    if add_answer != answer:
        wrong[add_answer] = "added_instead_of_subtracted"

    return Problem(topic="Fractions", difficulty=4, prompt=prompt,
                   correct_answer=answer, solution_steps=steps,
                   common_wrong_answers=wrong)


def _multiply(rng: random.Random) -> Problem:
    d1 = rng.randint(2, 9)
    d2 = rng.randint(2, 9)
    a = rng.randint(1, d1 - 1)
    b = rng.randint(1, d2 - 1)

    res_num = a * b
    res_den = d1 * d2
    answer = _fmt(res_num, res_den)
    sn, sd = _simplify(res_num, res_den)

    prompt = f"What is {a}/{d1} x {b}/{d2}? (Simplify your answer)"
    steps = [
        f"Multiply numerators: {a} x {b} = {res_num}",
        f"Multiply denominators: {d1} x {d2} = {res_den}",
        f"Result: {res_num}/{res_den}",
    ]
    if (sn, sd) != (res_num, res_den):
        steps.append(f"Simplify: {res_num}/{res_den} = {_fmt(res_num, res_den)}")

    wrong: dict[str, str] = {}
    # Forgot to simplify
    if (sn, sd) != (res_num, res_den):
        unsimplified = f"{res_num}/{res_den}"
        if unsimplified != answer:
            wrong[unsimplified] = "forgot_to_simplify"
    # Accidentally added instead of multiplied
    common = _lcd(d1, d2)
    add_num = a * (common // d1) + b * (common // d2)
    add_answer = _fmt(add_num, common)
    if add_answer != answer and add_answer not in wrong:
        wrong[add_answer] = "added_instead_of_multiplied"

    return Problem(topic="Fractions", difficulty=5, prompt=prompt,
                   correct_answer=answer, solution_steps=steps,
                   common_wrong_answers=wrong)


# ---------------------------------------------------------------------------
# Shared error patterns
# ---------------------------------------------------------------------------

def _addition_errors(a: int, b: int, d1: int, d2: int,
                     answer: str, raw_num: int, raw_den: int) -> dict[str, str]:
    """Common wrong answers for fraction addition problems."""
    wrong: dict[str, str] = {}

    # Classic mistake: add both numerators AND denominators
    bad = _fmt(a + b, d1 + d2)
    if bad != answer:
        wrong[bad] = "added_denominators"

    # Correct numerator/denominator but didn't simplify
    sn, sd = _simplify(raw_num, raw_den)
    if (sn, sd) != (raw_num, raw_den):
        unsimplified = f"{raw_num}/{raw_den}"
        if unsimplified != answer and unsimplified not in wrong:
            wrong[unsimplified] = "forgot_to_simplify"

    return wrong

