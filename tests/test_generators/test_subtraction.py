"""Tests for the subtraction generator."""

import random
import re
import pytest
from generators.subtraction import generate
from tests.conftest import SEED_COUNT

SEEDS = range(SEED_COUNT)


class TestCorrectness:
    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_answer_matches_difference(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        numbers = [int(x) for x in re.findall(r"\d+", p.prompt)]
        # First number minus each subsequent number
        expected = numbers[0]
        for n in numbers[1:]:
            expected -= n
        assert int(p.correct_answer) == expected

    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_answer_non_negative(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        assert int(p.correct_answer) >= 0


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
        assert p.topic == "Subtraction"
        assert p.difficulty == difficulty
        assert p.prompt
        assert p.correct_answer
        assert len(p.solution_steps) >= 1

