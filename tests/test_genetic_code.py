"""Unit tests for genetic_code.py."""
from logging import DEBUG, Logger, NullHandler, getLogger
from random import randint

from numpy import int64
from numpy.typing import NDArray

from egp_stores.gene_pool_cache import GPC_DEFAULT_SIZE, INT64_MAX
from egp_types.genetic_code import genetic_code


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


def test_genetic_code() -> None:
    """Fill the store with the genetic code.
    Verify empty genetic codes are what we expect.
    """
    _logger.debug("Gene pool generation started.")
    gene_pool: list[genetic_code] = [genetic_code() for _ in range(GPC_DEFAULT_SIZE)]
    _logger.debug("Gene pool generation completed.")
    assert gene_pool
    assert len(gene_pool) == GPC_DEFAULT_SIZE


def test_purge_basic() -> None:
    """Test the purge function when no genetic codes link to each other.
    The purge function should remove 25% of the genetic codes 4 times
    resulting in the oldest genetic code being in position 0.
    """
    genetic_code.reset()
    ids: list[int] = [id(genetic_code()) for _ in range(GPC_DEFAULT_SIZE * 2)]

    # The store should be full.
    assert len(genetic_code.gene_pool_cache) == GPC_DEFAULT_SIZE

    # Expecting the oldest genetic code to be in position 0 & max to be in position GPC_DEFAULT_SIZE - 1
    assert genetic_code.gene_pool_cache.access_sequence.argmin() == 0
    assert genetic_code.gene_pool_cache.access_sequence.argmax() == GPC_DEFAULT_SIZE - 1

    # Expecting the GPC_DEFAULT_SIZE element of the id list to be in position 0
    # and the last id to be in the last position
    assert id(genetic_code.gene_pool_cache.genetic_code[0]) == ids[GPC_DEFAULT_SIZE]
    assert id(genetic_code.gene_pool_cache.genetic_code[-1]) == ids[-1]


def test_purge_complex() -> None:
    """Test the purge function after a random access pattern.
    The purge should remove the oldest accessed 25% of the genetic codes
    and start filling those positionss with new genetic codes.
    """
    # Fill the gene pool
    _logger.debug("Gene pool generation started.")
    genetic_code.reset()
    for _ in range(GPC_DEFAULT_SIZE):
        genetic_code()

    # Randomly access genetic codes
    _logger.debug("Random access started.")
    for _ in range(GPC_DEFAULT_SIZE * 10):
        idx: int = randint(0, GPC_DEFAULT_SIZE - 1)
        genetic_code.gene_pool_cache[idx].touch()

    # Add a genetic code causing a purge
    _logger.debug("Trigger purge.")
    genetic_code()

    # There should be nothing older than the youngest purged genetic code.
    _logger.debug("Validate purge.")
    empty_indices: set[int] = set(genetic_code.gene_pool_cache.empty_indices())
    for idx, access in enumerate(genetic_code.gene_pool_cache.access_sequence):
        assert (idx in empty_indices) == (access == INT64_MAX)


def test_random_genetic_code() -> None:
    """Test the random genetic code function.
    The random genetic code method creates a binary tree structure with
    rndm+1 depth. 
    """
    levels = 15
    genetic_code.reset(2**(levels + 1))
    gc = genetic_code({"rndm": levels})
    genetic_code.gene_pool_cache.assertions()
    assert len(genetic_code.gene_pool_cache) == 2**(levels + 1) - 1
    assert gc["generation"] == levels
    assert gc.signature()


if __name__ == "__main__":
    test_random_genetic_code()
