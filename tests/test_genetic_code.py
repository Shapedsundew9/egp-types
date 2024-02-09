"""Unit tests for genetic_code.py."""
from logging import DEBUG, Logger, NullHandler, getLogger
from random import randint

from numpy import int64
from numpy.typing import NDArray

from egp_stores.gene_pool_cache import GPC_DEFAULT_SIZE
from egp_types._genetic_code import FIRST_ACCESS_NUMBER
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
    # Since all genetic codes are made the same way in this test the number of accesses
    # to create them is the same for all genetic codes.
    # Reset the data store and create a genetic code.
    genetic_code.reset()
    genetic_code()
    genetic_code()
    num_touches: int = genetic_code.gene_pool_cache.access_sequence[1] - genetic_code.gene_pool_cache.access_sequence[0]
    _logger.debug(f"Number of accesses to create a genetic code: {num_touches}")
    for _ in range(GPC_DEFAULT_SIZE * 2 - 2):
        genetic_code()

    # The size of the data store plus the empty and purged instances.
    assert len(genetic_code.gene_pool_cache) == GPC_DEFAULT_SIZE

    # The oldest access should be the first genetic code in the store.
    last_access: int = FIRST_ACCESS_NUMBER + GPC_DEFAULT_SIZE * num_touches
    assert genetic_code.gene_pool_cache.access_sequence[0] == last_access

    # See if the allocations are correct.
    for gc_access_num in genetic_code.gene_pool_cache.access_sequence:
        assert gc_access_num == last_access
        last_access += num_touches


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
        genetic_code.gene_pool_cache[randint(0, GPC_DEFAULT_SIZE - 1)].touch()

    # Add a genetic code causing a purge
    _logger.debug("Trigger purge.")
    genetic_code()

    # There should be nothing older than the youngest purged genetic code.
    _logger.debug("Validate purge.")
    oldest_accesses: NDArray[int64] = genetic_code.gene_pool_cache.access_sequence[genetic_code.gene_pool_cache.empty_indices]
    newest_oldest_access: int64 = oldest_accesses.max()
    for indx, gc_access_num in enumerate(genetic_code.gene_pool_cache.access_sequence):
        assert gc_access_num > newest_oldest_access or indx in genetic_code.gene_pool_cache.empty_indices


def test_random_genetic_code() -> None:
    """Test the random genetic code function.
    The random genetic code method creates a binary tree structure with
    rndm+1 depth. 
    """
    genetic_code.reset()
    genetic_code({"rndm": 5})
    genetic_code.gene_pool_cache.assertions()
    assert len(genetic_code.gene_pool_cache) == 2**6 - 1
