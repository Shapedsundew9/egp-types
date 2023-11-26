"""Test cases for the internal graph module."""
from functools import partial
from itertools import count
from json import dump, load
from logging import DEBUG, INFO, Logger, NullHandler, getLogger
from os.path import dirname, exists, join
from pprint import pformat
from random import seed, choice
import pytest
from tqdm import trange

from egp_types.eGC import set_reference_generator
from egp_types.end_point import dst_end_point, src_end_point
from egp_types.gc_graph import gc_graph
from egp_types.graph_validators import limited_igraph_validator as liv
from egp_types.internal_graph import (internal_graph, internal_graph_from_json,
                                      random_internal_graph)
from egp_types.reference import reference
from egp_types.egp_typing import VALID_GRAPH_ROW_COMBINATIONS


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
getLogger("surebrec").setLevel(INFO)
getLogger("eGC").setLevel(INFO)
getLogger("ep_type").setLevel(INFO)


# Reference generation for eGC's
ref_generator = partial(reference, gpspuid=127, counter=count())
set_reference_generator(ref_generator)


NUM_RANDOM_GRAPHS = 4000
FILENAME: str = join(dirname(__file__), "data/random_internal_graph.json")
COMBOS = tuple(VALID_GRAPH_ROW_COMBINATIONS)
if not exists(FILENAME):
    seed(1)
    with open(FILENAME, "w", encoding="utf-8") as f:
        dump([random_internal_graph(choice(COMBOS), verify=True, rseed=rseed).json_obj() for rseed in trange(NUM_RANDOM_GRAPHS)], f, indent=4, sort_keys=True)

with open(FILENAME, "r", encoding="utf-8") as f:
    RANDOM_GRAPHS: list[internal_graph] = [internal_graph_from_json(json_igraph) for json_igraph in load(f)]


@pytest.mark.parametrize("igraph", RANDOM_GRAPHS)
def test_to_json_from_json(igraph: internal_graph) -> None:
    """Test that a random internal graph is a valid (but not necessarily stable) gc_graph."""
    json_igraph: dict[str, list[str | int | bool | list[list[str | int]] | None]] = igraph.json_obj()
    igraph2: internal_graph = internal_graph_from_json(json_igraph)
    if _LOG_DEBUG and igraph != igraph2:
        _logger.debug(f"json_igraph:\n{pformat(json_igraph)}")
        _logger.debug(f"igraph:\n{igraph}")
        _logger.debug(f"igraph2:\n{igraph2}")
    assert igraph == igraph2


@pytest.mark.parametrize("igraph", RANDOM_GRAPHS)
def test_random_internal_graph_as_gc_graph(igraph) -> None:
    """Test that a random internal graph is a valid (but not necessarily stable) gc_graph."""
    gcg = gc_graph(i_graph=igraph)
    gcg.normalize()
    assert gcg.validate()

