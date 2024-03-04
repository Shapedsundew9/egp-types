"""Tests for the graph class."""
from functools import partial
from itertools import count
from logging import DEBUG, Logger, NullHandler, getLogger
from random import choice, seed
from pprint import pformat

import pytest

from egp_types.egp_typing import VALID_GRAPH_ROW_COMBINATIONS, JSONGraph
from egp_types.genetic_code import graph
from egp_types.graph_validators import graph_validator


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Constants
VALID_COMBOS = tuple(VALID_GRAPH_ROW_COMBINATIONS)


# Random seed
seed(1)


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
    grph: graph = graph(TEST_GRAPH)
    grph.assertions()
    _logger.debug(f"Graph data:\n{repr(grph)}")
    _logger.debug(f"Graph Mermaid Chart:\n{grph}")


@pytest.mark.parametrize("_", list(range(1000)))
def test_random_graph(_) -> None:
    """Test the random graph function generates a valid graph that can be converted to JSON
    and back again to a graph. The two graphs should be equal."""
    g1 = graph({}, rows=choice(VALID_COMBOS), rndm=True, verify=True)
    # _logger.debug(f"Random graph:\n{repr(g1)}")
    json_graph: JSONGraph = g1.json_graph()
    # _logger.debug(f"Random JSON graph:\n{pformat(json_graph)}")
    valid: bool = graph_validator.validate({"graph": json_graph})
    if not valid:
        _logger.error(f"Invalid JSON graph:\n{graph_validator.error_str()}\n{pformat(json_graph)}")
        assert valid, "Invalid JSON graph. See logs."
    g2 = graph(json_graph)
    equal: bool = g1 == g2
    if not equal:
        _logger.error(f"Graphs are not equal:\n{repr(g1)}\n{repr(g2)}")
        assert equal, "Graphs are not equal. See logs."
