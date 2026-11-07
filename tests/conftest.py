"""Shared test fixtures for MathForge.

Key convention: every generator test uses a *range* of seeds so we exercise
many random paths, and a fixed seed for reproducibility checks.
"""

# Number of random seeds used by parametrized correctness tests.
# 20 seeds x 5 difficulties = 100 combinations per generator — good
# coverage without making the test run slow.
SEED_COUNT = 20

