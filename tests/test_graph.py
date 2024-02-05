"""Tests for the graph class."""
import pytest
from functools import partial
from itertools import count
from logging import DEBUG, Logger, NullHandler, getLogger

from egp_types.eGC import set_reference_generator
from egp_types.egp_typing import JSONGraph
from egp_types.genetic_code import EGC_TRIPLE, graph
from egp_types.reference import reference


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Reference generation for eGC's
ref_generator = partial(reference, gpspuid=127, counter=count())
set_reference_generator(ref_generator)

# GC_GRAPH = gc_graph(i_graph=random_internal_graph("ICFABOP", ep_types=(2,), verify=True, rseed=1, row_stablization=True))
# GC_GRAPH.normalize()
# assert GC_GRAPH.validate()
# TEST_GRAPH: JSONGraph = connection_graph_to_json(GC_GRAPH.connection_graph())
# print(TEST_GRAPH)
TEST_GRAPH: JSONGraph = {
    "A": [["C", 5, 2], ["I", 1, 2], ["C", 6, 2], ["I", 1, 2], ["C", 3, 2], ["C", 4, 2], ["C", 4, 2]],
    "B": [["I", 2, 2]],
    "F": [["I", 0, 1]],
    "O": [["C", 7, 2], ["C", 5, 2], ["I", 1, 2], ["A", 0, 2], ["C", 6, 2], ["C", 2, 2], ["C", 5, 2], ["C", 5, 2]],
    "P": [["C", 6, 2], ["B", 2, 2], ["C", 1, 2], ["C", 4, 2], ["C", 7, 2], ["I", 1, 2], ["C", 6, 2], ["C", 7, 2]],
    "U": [["B", 0, 2], ["B", 1, 2], ["B", 3, 2], ["C", 0, 2]],
    "C": [["42", 2], ["64", 2], ["-75", 2], ["-53", 2], ["61", 2], ["85", 2], ["-25", 2], ["-70", 2]],
}


def test_graph_mermaid() -> None:
    """Test the mermaid function."""
    grph: graph = graph(TEST_GRAPH, *EGC_TRIPLE)
    grph.assertions()
    _logger.debug(f"Graph data:\n{repr(grph)}")
    _logger.debug(f"Graph Mermaid Chart:\n{grph}")


@pytest.mark.parametrize("_", list(range(1000)))
def test_random_graph(_) -> None:
    """Test the random graph function."""
    grph: graph = graph({}, *EGC_TRIPLE, rndm=True, rseed=1, verify=True)