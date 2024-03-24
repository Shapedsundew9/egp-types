"""Unit tests for genetic_code.py."""
from logging import DEBUG, Logger, NullHandler, getLogger
from random import randint
from egp_types.genetic_code_cache import genetic_code_cache, GCC_DEFAULT_SIZE, INT64_MAX
from egp_types.genetic_code import genetic_code_factory


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


def test_genetic_code_cache() -> None:
    """Fill the store with the genetic code.
    Verify empty genetic codes are what we expect.
    """
    _logger.debug("Genetic Code Cache generation started.")
    gcc: genetic_code_cache = genetic_code_cache(genetic_code_factory())
    for _ in range(GCC_DEFAULT_SIZE):
        gcc.genetic_code_type({}, rndm=True, depth=0, rseed=1)
    _logger.debug("Genetic Code Cache generation completed.")
    assert gcc
    assert len(gcc) == GCC_DEFAULT_SIZE


def test_purge_basic() -> None:
    """Test the purge function when no genetic codes link to each other.
    The purge function should remove 25% of the genetic codes 4 times
    resulting in the oldest genetic code being in position 0.
    """
    gcc: genetic_code_cache = genetic_code_cache(genetic_code_factory())
    for _ in range(GCC_DEFAULT_SIZE * 2):
        gcc.genetic_code_type({}, rndm=True, depth=0, rseed=1)

    # The store should be full.
    assert len(gcc) == GCC_DEFAULT_SIZE

    # Expecting the oldest genetic code to be in position 0 & max to be in position GCC_DEFAULT_SIZE - 1
    assert gcc.access_sequence.argmin() == 0
    assert gcc.access_sequence.argmax() == GCC_DEFAULT_SIZE - 1


def test_purge_complex() -> None:
    """Test the purge function after a random access pattern.
    The purge should remove the oldest accessed 25% of the genetic codes
    and start filling those positionss with new genetic codes.
    """
    # Fill the Genetic Code Cache
    gcc: genetic_code_cache = genetic_code_cache(genetic_code_factory())
    for _ in range(GCC_DEFAULT_SIZE):
        gcc.genetic_code_type({}, rndm=True, depth=0, rseed=1)

    # Randomly access genetic codes
    _logger.debug("Random access started.")
    for _ in range(GCC_DEFAULT_SIZE * 10):
        idx: int = randint(0, GCC_DEFAULT_SIZE - 1)
        gcc[idx].touch()

    # Add a genetic code causing a purge
    _logger.debug("Trigger purge.")
    gcc.genetic_code_type({}, rndm=True, depth=0, rseed=1)

    # There should be nothing older than the youngest purged genetic code.
    _logger.debug("Validate purge.")
    empty_indices: set[int] = set(gcc.empty_indices())
    for idx, access in enumerate(gcc.access_sequence):
        assert (idx in empty_indices) == (access == INT64_MAX)


def test_random_genetic_code() -> None:
    """Test the random genetic code function.
    The random genetic code method creates a binary tree structure with
    rndm+1 depth.
    """
    levels = 5
    gcc: genetic_code_cache = genetic_code_cache(genetic_code_factory(), size=64)
    gcc.genetic_code_type({}, rndm=True, depth=levels, rseed=1)

    gcc.assertions()
    assert len(gcc) == 2 ** (levels + 1) - 1
    assert gcc[0]["generation"] == levels
    assert gcc[0].signature().sum() != 0


if __name__ == "__main__":
    test_random_genetic_code()
