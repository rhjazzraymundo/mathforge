"""Tests for the division generator."""

import random
import re
import pytest
from generators.division import generate
from tests.conftest import SEED_COUNT

SEEDS = range(SEED_COUNT)


class TestCorrectness:
    @pytest.mark.parametrize("seed", SEEDS)
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_answer_is_correct(self, seed, difficulty):
        p = generate(difficulty, random.Random(seed))
        numbers = [int(x) for x in re.findall(r"\d+", p.prompt)]
        dividend, divisor = numbers[0], numbers[1]

        if "r" in p.correct_answer:
            # Remainder format "Q r R"
            parts = p.correct_answer.split("r")
            q = int(parts[0].strip())
            r = int(parts[1].strip())
            assert divisor * q + r == dividend, (
                f"{dividend}/{divisor}: expected Q={q}, R={r} to satisfy "
                f"{divisor}*{q}+{r}={dividend}"
            )
            assert 0 < r < divisor, f"Remainder {r} out of range for divisor {divisor}"
        else:
            quotient = int(p.correct_answer)
            assert divisor * quotient == dividend

    @pytest.mark.parametrize("seed", SEEDS)
    def test_exact_difficulties_have_no_remainder(self, seed):
        """Difficulties 1, 2, 4 should always produce exact divisions."""
        for diff in (1, 2, 4):
            p = generate(diff, random.Random(seed))
            assert "r" not in p.correct_answer, (
                f"Difficulty {diff} should be exact but got: {p.correct_answer}"
            )

    @pytest.mark.parametrize("seed", SEEDS)
    def test_remainder_difficulties_have_remainder(self, seed):
        """Difficulties 3, 5 should always have a remainder."""
        for diff in (3, 5):
            p = generate(diff, random.Random(seed))
            assert "r" in p.correct_answer, (
                f"Difficulty {diff} should have remainder but got: {p.correct_answer}"
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
        for wrong in p.common_wrong_answers:
            assert wrong != p.correct_answer


class TestFields:
    @pytest.mark.parametrize("difficulty", range(1, 6))
    def test_fields_present(self, difficulty):
        p = generate(difficulty, random.Random(0))
        assert p.topic == "Division"
        assert p.difficulty == difficulty
        assert p.prompt
        assert p.correct_answer
        assert len(p.solution_steps) >= 1

