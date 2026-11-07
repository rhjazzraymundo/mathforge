"""Core data model for math problems.

Every generator returns a Problem instance.  The dataclass is deliberately
simple — it carries the problem text, the correct answer, step-by-step
solution, and a map of plausible wrong answers to error tags.
"""

from dataclasses import dataclass, field


@dataclass
class Problem:
    """A single math problem with its solution and common mistakes.

    Attributes:
        topic:                Topic name, e.g. "Addition".
        difficulty:           1-5 scale.
        prompt:               The question shown to the student.
        correct_answer:       Canonical string form of the correct answer.
        solution_steps:       Ordered list of human-readable solution steps.
        common_wrong_answers: Maps a plausible wrong answer string to an
                              error-tag like "forgot_to_carry".  Used for
                              targeted feedback and analytics.
    """

    topic: str
    difficulty: int
    prompt: str
    correct_answer: str
    solution_steps: list[str] = field(default_factory=list)
    common_wrong_answers: dict[str, str] = field(default_factory=dict)

