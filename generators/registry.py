"""Topic → generator registry.

To add a new topic:
  1. Create a new module in generators/ with a `generate(difficulty, rng)` function.
  2. Import it below and add an entry to REGISTRY.

This is intentionally explicit (no auto-discovery magic) so you can see
every available topic by reading this one file.
"""

from typing import Callable
import random
from generators.models import Problem

# Type alias for a generator function
GeneratorFn = Callable[[int, random.Random], Problem]

from generators.addition import generate as _addition
from generators.subtraction import generate as _subtraction
from generators.multiplication import generate as _multiplication
from generators.division import generate as _division
from generators.fractions_gen import generate as _fractions

REGISTRY: dict[str, GeneratorFn] = {
    "Addition": _addition,
    "Subtraction": _subtraction,
    "Multiplication": _multiplication,
    "Division": _division,
    "Fractions": _fractions,
}


def get_generator(topic: str) -> GeneratorFn:
    """Return the generator function for *topic*, or raise KeyError."""
    if topic not in REGISTRY:
        raise KeyError(f"Unknown topic: {topic!r}. Available: {list_topics()}")
    return REGISTRY[topic]


def list_topics() -> list[str]:
    """Sorted list of all registered topic names."""
    return sorted(REGISTRY.keys())

