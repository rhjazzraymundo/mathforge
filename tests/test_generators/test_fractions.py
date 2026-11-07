"""Tests for the fractions generator.

Uses Python's built-in fractions.Fraction to independently verify
that the generator's answer is mathematically correct, regardless
of how the generator computes it internally.
"""

import math
import random
import re
import pytest
from fractions import Fraction
from generators.fractions_gen import generate
from tests.conftest import SEED_COUNT

SEEDS = range(SEED_COUNT)


def _parse_answer(s: str) -> Fraction:
    """Parse '3/4' or '2' into a Fraction."""
    s = s.strip()
    if "/" in s:
        num, den = s.split("/")
        return Fraction(int(num), int(den))
    return Fraction(int(s))


def _compute_expected(prompt: str) -> Fraction:
    """Parse the prompt and compute the expected answer independently.

    Handles prompts like:
      'What is 2/3 + 1/4? (Simplify your answer)'
      'What is 3/4 - 1/3? (Simplify your answer)'
      'What is 2/5 x 3/7? (Simplify your answer)'
    """
    m = re.search(r"(\d+)/(\d+)\s*([+\-x])\s*(\d+)/(\d+)", prompt)
    assert m, f"Could not parse prompt: {prompt}"
    a, b, op, c, d = int(m[1]), int(m[2]), m[3], int(m[4]), int(m[5])
    f1, f2 = Fraction(a, b), Fraction(c, d)
    if op == "+":
        return f1 + f2
    if op == "-":
        return f1 - f2
    if op == "x":
        return f1 * f2
    raise ValueError(f"Unknown operator: {op!r}")


class TestCorrectness:
    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_answer_matches_independent_computation(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        expected = _compute_expected(p.prompt)
        actual = _parse_answer(p.correct_answer)
        assert actual == expected, (
            f"Prompt: {p.prompt}\n"
            f"  Generator answer: {p.correct_answer} ({actual})\n"
            f"  Expected:         {expected}"
        )

    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_answer_is_fully_simplified(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        if "/" in p.correct_answer:
            num, den = p.correct_answer.split("/")
            assert math.gcd(abs(int(num)), int(den)) == 1, (
                f"Answer {p.correct_answer} is not fully simplified"
            )


class TestReproducibility:
    @pytest.mark.parametrize("seed", [0, 42, 999])
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_deterministic(self, seed, difficulty):
        p1 = generate(difficulty, random.Random(seed))
        p2 = generate(difficulty, random.Random(seed))
        assert p1.prompt == p2.prompt
        assert p1.correct_answer == p2.correct_answer


class TestWrongAnswersAreWrong:
    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_no_false_positives(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        actual = _parse_answer(p.correct_answer)
        for wrong_str in p.common_wrong_answers:
            wrong_val = _parse_answer(wrong_str)
            assert wrong_val != actual, (
                f"Wrong answer '{wrong_str}' equals correct for: {p.prompt}"
            )


class TestFields:
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_fields_present(self, difficulty):
        p = generate(difficulty, random.Random(0))
        assert p.topic == "Fractions"
        assert p.difficulty == difficulty
        assert p.prompt
        assert p.correct_answer
        assert len(p.solution_steps) >= 1

