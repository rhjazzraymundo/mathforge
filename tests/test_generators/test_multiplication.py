"""Tests for the multiplication generator."""

import random
import re
import pytest
from generators.multiplication import generate
from tests.conftest import SEED_COUNT

SEEDS = range(SEED_COUNT)


class TestCorrectness:
    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_answer_matches_product(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        numbers = [int(x) for x in re.findall(r"\d+", p.prompt)]
        assert int(p.correct_answer) == numbers[0] * numbers[1]


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
        for wrong in p.common_wrong_answers:
            assert wrong != p.correct_answer


class TestFields:
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_fields_present(self, difficulty):
        p = generate(difficulty, random.Random(0))
        assert p.topic == "Multiplication"
        assert p.difficulty == difficulty
        assert p.prompt
        assert p.correct_answer
        assert len(p.solution_steps) >= 1

