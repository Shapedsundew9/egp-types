"""Unit tests for genetic_code.py."""
from json import dump, load
from logging import DEBUG, INFO, Logger, NullHandler, getLogger
from os.path import dirname, exists, join
from random import randint

from numpy import int64
from numpy.typing import NDArray
from tqdm import trange

from egp_types.egp_typing import ConnectionGraph, DstRowIndex, JSONGraph, SrcRowIndex, connection_graph_to_json, json_to_connection_graph
from egp_types.gc_graph import gc_graph, random_gc_graph
from egp_types.genetic_code import DEFAULT_STORE_SIZE, EMPTY_GENETIC_CODE, FIRST_ACCESS_NUMBER, genetic_code
from egp_types.graph_validators import graph_validator
from egp_types.interface import EMPTY_INTERFACE, EMPTY_INTERFACE_C

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
getLogger("surebrec").setLevel(INFO)
getLogger("eGC").setLevel(INFO)
getLogger("ep_type").setLevel(INFO)
getLogger("gc_graph").setLevel(INFO)

_RANDOM_GRAPHS_JSON = "data/random_graphs.json"
NUM_TEST_CASES = 200


# Generating graphs is slow so we generate them once as needed
if not exists(join(dirname(__file__), _RANDOM_GRAPHS_JSON)):
    json_graphs: list[JSONGraph] = [
        connection_graph_to_json(random_gc_graph(graph_validator, True, i).connection_graph()) for i in trange(1000)
    ]
    with open(join(dirname(__file__), _RANDOM_GRAPHS_JSON), "w", encoding="utf-8") as random_file:
        dump(json_graphs, random_file, indent=4)

_logger.debug("Loading random graphs (can take a while)...")
with open(join(dirname(__file__), _RANDOM_GRAPHS_JSON), "r", encoding="utf-8") as random_file:
    connection_graphs: list[ConnectionGraph] = [json_to_connection_graph(j_graph) for j_graph in load(random_file)]
random_graphs: list[gc_graph] = []
for idx, random_graph in enumerate(connection_graphs):
    _logger.debug(f"Random graph index: {idx}")
    random_graphs.append(gc_graph(random_graph))
_logger.debug("Random graphs loaded.")


def test_genetic_code() -> None:
    """Fill the store with the genetic code.
    Verify empty genetic codes are what we expect.
    """
    _logger.debug("Gene pool generation started.")
    gene_pool: list[genetic_code] = [genetic_code() for _ in range(DEFAULT_STORE_SIZE)]
    _logger.debug("Gene pool generation completed.")
    assert gene_pool
    assert len(gene_pool) == DEFAULT_STORE_SIZE
    for gc in gene_pool:
        assert gc
        assert gc.gca is EMPTY_GENETIC_CODE
        assert gc.gcb is EMPTY_GENETIC_CODE
        assert gc.ancestor_a is EMPTY_GENETIC_CODE
        assert gc.ancestor_b is EMPTY_GENETIC_CODE
        assert gc.graph.rows[SrcRowIndex.I] is EMPTY_INTERFACE
        assert gc.graph.rows[SrcRowIndex.C] is EMPTY_INTERFACE_C
        assert gc.graph.rows[DstRowIndex.F] is EMPTY_INTERFACE
        assert gc.graph.rows[SrcRowIndex.A] is EMPTY_INTERFACE
        assert gc.graph.rows[DstRowIndex.A] is EMPTY_INTERFACE
        assert gc.graph.rows[SrcRowIndex.B] is EMPTY_INTERFACE
        assert gc.graph.rows[DstRowIndex.B] is EMPTY_INTERFACE
        assert gc.graph.rows[DstRowIndex.O] is EMPTY_INTERFACE
        assert gc.graph.rows[DstRowIndex.P] is EMPTY_INTERFACE

    _logger.debug("Gene pool validation completed.")


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
    num_touches: int = genetic_code.data_store.access_sequence[1] - genetic_code.data_store.access_sequence[0]
    _logger.debug(f"Number of accesses to create a genetic code: {num_touches}")
    for _ in range(DEFAULT_STORE_SIZE * 2 - 2):
        genetic_code()

    # The size of the data store plus the empty and purged instances.
    assert genetic_code.num_nodes == DEFAULT_STORE_SIZE

    # The oldest access should be the first genetic code in the store.
    last_access: int = FIRST_ACCESS_NUMBER + DEFAULT_STORE_SIZE * num_touches
    assert genetic_code.data_store.access_sequence[0] == last_access

    # See if the allocations are correct.
    for gc_access_num in genetic_code.data_store.access_sequence:
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
    for _ in range(DEFAULT_STORE_SIZE):
        genetic_code()

    # Randomly access genetic codes
    _logger.debug("Random access started.")
    for _ in range(DEFAULT_STORE_SIZE * 10):
        genetic_code.data_store[randint(0, DEFAULT_STORE_SIZE - 1)].touch()

    # Add a genetic code causing a purge
    _logger.debug("Trigger purge.")
    genetic_code()

    # There should be nothing older than the youngest purged genetic code.
    _logger.debug("Validate purge.")
    oldest_accesses: NDArray[int64] = genetic_code.data_store.access_sequence[genetic_code.data_store.empty_indices]
    newest_oldest_access: int64 = oldest_accesses.max()
    for indx, gc_access_num in enumerate(genetic_code.data_store.access_sequence):
        assert gc_access_num > newest_oldest_access or indx in genetic_code.data_store.empty_indices


def test_loading_random_connection_graphs() -> None:
    """Test loading random connection graphs from a JSON file."""
    genetic_code.reset()
    _logger.debug("Loading random connection graphs in to genetic codes.")
    for graph in connection_graphs:
        genetic_code({"graph": graph})
    _logger.debug("Validating load.")
    assert len(genetic_code.data_store) == len(connection_graphs)
    genetic_code.data_store.assertions()

