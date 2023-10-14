"""gc_graph verficiation."""

from copy import deepcopy
from functools import partial
from itertools import count
from json import load
from logging import DEBUG, Logger, NullHandler, getLogger
from os.path import dirname, join
from random import choice, randint, random
from typing import Any

import pytest

from egp_types import reference, set_reference_generator
from egp_types.egp_typing import (
    DST_EP,
    SRC_EP,
    json_to_connection_graph,
)
from egp_types.ep_type import (
    EP_TYPE_VALUES,
    INVALID_EP_TYPE_VALUE,
    asint
)
from egp_types.gc_graph import gc_graph, random_gc_graph
from egp_types.xgc_validator import graph_validator

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
_TEST_RESULTS_JSON = "data/test_gc_graph_results.json"


# Reference generation for eGC's
ref_generator = partial(reference, gpspuid=127, counter=count())
set_reference_generator(ref_generator)


# JSON cannot represent the ConnectionGraph type so a conversion step is needed.
with open(join(dirname(__file__), _TEST_RESULTS_JSON), "r", encoding="utf-8") as results_file:
    results: list[dict[str, Any]] = load(results_file)
for result in results:
    result["graph"] = json_to_connection_graph(result["graph"])


def random_type(probability: float = 0.0) -> int:
    """Choose a random type.

    If a random type is selected the probability of each type is even.
    By default 'int' is returned.

    Args
    ----
    probability: Probablity that the type is random (otherwise it is an 'int')

    Returns
    -------
    The selected type integer value.
    """
    if random() < probability:
        value: int = choice(tuple(EP_TYPE_VALUES))
        if value != INVALID_EP_TYPE_VALUE:
            return value
    return asint("builtins_int")


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_validation(i, case) -> None:
    """Verification the validate() method correctly functions."""
    gcg = gc_graph(case["graph"])
    assert i == case["i"]
    assert case["valid"] == gcg.validate()
    if not case["valid"]:
        assert all([e in [g.code for g in gcg.status] for e in case["errors"]])


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_str(i, case) -> None:
    """Verification the __repr__() method is not broken."""
    _logger.debug(f"Case {i}")
    gcg = gc_graph(case["graph"])
    assert str(gcg)


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_draw(i, case) -> None:
    """Verification the draw() method is not broken."""
    gcg = gc_graph(case["graph"])
    if case["valid"]:
        gcg.draw(join(dirname(__file__), "../logs/gc_graph_" + str(i)))


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_internal(i, case) -> None:
    """Verification initializing with an internal representation is self consistent."""
    gcg = gc_graph(case["graph"])
    _logger.debug(f"Case {i}")
    assert gcg.connection_graph() == gc_graph(i_graph=deepcopy(gcg.i_graph)).connection_graph()


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_conversion(i, case) -> None:
    """Verification that converting to internal format and back again is the identity operation."""
    gcg = gc_graph(case["graph"])
    assert i == case["i"]
    if case["valid"]:
        assert case["graph"] == gcg.connection_graph()


@pytest.mark.parametrize("test", range(100))
def test_remove_connection_simple(test) -> None:
    """Verify adding connections makes valid graphs.

    Create a random graph remove some connections & re-normalise.
    To keep it simple all the endpoints -> None have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    _logger.debug(f"Case {test}")
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    # TOD: gc_graphO: Split this out into its own test case when the graphs are staticly defined in a JSON file.
    graph.random_remove_connection(int(sum(graph.rows[DST_EP].values()) / 2))
    graph.normalize()
    assert graph.validate()
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("_", range(100))
def test_add_input_simple(_) -> None:
    """Verify adding inputs makes valid graphs.

    Create a random graph, add an input & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    before: int = graph.rows[SRC_EP].get("I", 0)
    graph.add_input()
    graph.normalize()
    after: int = graph.rows[SRC_EP].get("I", 0)
    assert graph.validate()
    assert after == before + 1
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("_", range(100))
def test_remove_input_simple(_) -> None:
    """Verify removing inputs makes valid graphs.

    Create a random graph, remove an input & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    before: int = graph.rows[SRC_EP].get("I", 0)
    graph.remove_input()
    graph.normalize()
    after: int = graph.rows[SRC_EP].get("I", 0)

    # E1001 & E01016 are a legit error when removing an input.
    if not graph.validate():
        codes = set([t.code for t in graph.status])
        codes.discard("E01001")
        codes.discard("E01016")
        assert not codes
    assert after == before - 1 if before else after == before == 0
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("_", range(100))
def test_add_output_simple(_) -> None:
    """Verify adding outputs makes valid graphs.

    Create a random graph, add an output & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    before: int = graph.rows[DST_EP].get("O", 0)
    graph.add_output()
    graph.normalize()
    after: int = graph.rows[DST_EP].get("O", 0)
    assert graph.validate()
    assert after == before + 1
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("_", range(100))
def test_remove_output_simple(_) -> None:
    """Verify removing outputs makes valid graphs.

    Create a random graph, remove an output & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    before: int = graph.rows[DST_EP].get("O", 0)
    graph.remove_output()
    graph.normalize()
    after: int = graph.rows[DST_EP].get("O", 0)

    # E1000 is a legit error when removing an output (no row O).
    if not graph.validate():
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard("E01006")
        assert not codes
    if before:
        assert after == before - 1
    else:
        assert after == before == 0
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("_", range(100))
def test_remove_constant_simple(_) -> None:
    """Verify removing contants makes valid graphs.

    Create a random graph, remove a constant & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    before: int = graph.rows[SRC_EP].get("C", 0)
    graph.remove_constant()
    graph.normalize()
    after: int = graph.rows[SRC_EP].get("C", 0)

    # E1001 is a legit error when removing an constant.
    if not graph.validate():
        codes = set([t.code for t in graph.status])
        codes.discard("E01001")
        assert not codes
    assert after == before - 1 if before else after == before == 0
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("_", range(100))
def test_binary_compound_modifications(_) -> None:
    """Verify compounding modifications still makes valid graphs.

    Create a random graph, do 2 random modifications & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    for _ in range(2):
        selection: int = randint(0, 4)
        match selection:
            case 0:
                graph.add_input()
            case 1:
                graph.remove_input()
            case 2:
                graph.add_output()
            case 3:
                graph.remove_output()
            case 4:
                graph.remove_constant()

    # E1000 & E1001 are legit errors when modifiying the graph
    graph.normalize()
    if not graph.validate():
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard("E01006")
        codes.discard("E01001")
        codes.discard("E01016")
        assert not codes


@pytest.mark.parametrize("_", range(100))
def test_nary_compound_modifications(_) -> None:
    """Verify compounding modifications still makes valid graphs.

    Create a random graph, do 3 to 20 random modifications & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph: gc_graph = random_gc_graph(graph_validator)
    assert graph.validate()

    for _ in range(randint(3, 20)):
        selection: int = randint(0, 4)
        match selection:
            case 0:
                graph.add_input()
            case 1:
                graph.remove_input()
            case 2:
                graph.add_output()
            case 3:
                graph.remove_output()
            case 4:
                graph.remove_constant()

    # E1000 & E1001 are legit errors when modifiying the graph
    graph.normalize()
    if not graph.validate():
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard("E01006")
        codes.discard("E01016")
        codes.discard("E01001")
        assert not codes
