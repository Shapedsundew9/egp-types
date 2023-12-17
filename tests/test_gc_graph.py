"""gc_graph verficiation."""

from copy import deepcopy
from functools import partial
from itertools import count
from json import dump, load
from logging import DEBUG, INFO, Logger, NullHandler, getLogger
from os.path import dirname, exists, join
from pprint import pformat
from random import choice, randint, random, seed, sample
from typing import Any

import pytest
from tqdm import trange

from egp_types.reference import reference
from egp_types.eGC import set_reference_generator
from egp_types.egp_typing import DST_EP, SRC_EP, JSONGraph, ConnectionGraph, connection_graph_to_json, json_to_connection_graph
from egp_types.ep_type import EP_TYPE_VALUES, INVALID_EP_TYPE_VALUE, asint, ep_type_lookup
from egp_types.gc_graph import gc_graph, random_gc_graph
from egp_types.graph_validators import graph_validator


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
getLogger("surebrec").setLevel(INFO)
getLogger("eGC").setLevel(INFO)
getLogger("ep_type").setLevel(INFO)
_TEST_RESULTS_JSON = "data/test_gc_graph_results.json"
_RANDOM_GRAPHS_JSON = "data/random_graphs.json"
NUM_TEST_CASES = 200

# Reference generation for eGC's
ref_generator = partial(reference, gpspuid=127, counter=count())
set_reference_generator(ref_generator)


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


# Random graph statistics
_logger.debug("Random graph statistics:")
_logger.info(f"# random graphs: {len(random_graphs)}")
_logger.info(f"# random graphs with no inputs: {len([graph for graph in random_graphs if not graph.rows[SRC_EP].get('I', 0)])}")
_logger.info(f"# random graphs with no outputs: {len([graph for graph in random_graphs if not graph.rows[DST_EP].get('O', 0)])}")
_logger.info(f"# random graphs with no constants: {len([graph for graph in random_graphs if not graph.rows[SRC_EP].get('C', 0)])}")
_logger.info(f"# random graphs with no row F: {len([graph for graph in random_graphs if not graph.rows[DST_EP].get('F', 0)])}")
_logger.info(f"# random graphs with no row P: {len([graph for graph in random_graphs if not graph.rows[DST_EP].get('P', 0)])}")
_logger.info(f"# random graphs with no row A srcs: {len([graph for graph in random_graphs if not graph.rows[SRC_EP].get('A', 0)])}")
_logger.info(f"# random graphs with no row B srcs: {len([graph for graph in random_graphs if not graph.rows[SRC_EP].get('B', 0)])}")
_logger.info(f"# random graphs with no row A dsts: {len([graph for graph in random_graphs if not graph.rows[DST_EP].get('A', 0)])}")
_logger.info(f"# random graphs with no row B dsts: {len([graph for graph in random_graphs if not graph.rows[DST_EP].get('B', 0)])}")


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


def test_ep_type_int_of_bool() -> None:
    """These tests assume bool is EP type 1.

    If that is not the case correct the test_gc_graph_results.json file 'F' rows
    """
    assert ep_type_lookup["n2v"]["bool"] == 1


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_validation(i, case) -> None:
    """Verification the validate() method correctly functions."""
    _logger.debug(f"Case {i}")
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
def test_graph_internal_simple(i, case) -> None:
    """Verification initializing with an internal representation is self consistent."""
    gcg = gc_graph(case["graph"])
    _logger.debug(f"Case {i}")
    assert gcg.connection_graph() == gc_graph(i_graph=deepcopy(gcg.i_graph)).connection_graph()


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_conversion_simple(i, case) -> None:
    """Verification that converting to internal format and back again is the identity operation."""
    gcg = gc_graph(case["graph"])
    assert i == case["i"]
    if case["valid"]:
        assert case["graph"] == gcg.connection_graph()


@pytest.mark.parametrize("i, gcg", enumerate(sample(random_graphs, NUM_TEST_CASES)))
def test_graph_internal(i, gcg) -> None:
    """Verification initializing with an internal representation is self consistent."""
    _logger.debug(f"Case {i}")
    assert gcg.connection_graph() == gc_graph(i_graph=deepcopy(gcg.i_graph)).connection_graph()


@pytest.mark.parametrize("i, case", enumerate(sample(list(range(len(random_graphs))), NUM_TEST_CASES)))
def test_graph_conversion(i, case) -> None:
    """Verification that converting to internal format and back again is the identity operation."""
    _logger.debug(f"Case {i}")
    assert connection_graphs[case] == random_graphs[case].connection_graph()


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_remove_connection_simple(test) -> None:
    """Verify adding connections makes valid graphs.

    Create a random graph remove some connections & re-normalise.
    To keep it simple all the endpoints -> None have the same type ("int").
    """
    seed(0)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

    graph.random_remove_connection(int(sum(graph.rows[DST_EP].values()) / 2))
    graph.normalize()
    passed: bool = graph.validate()
    if not passed:
        _logger.debug(f"Initial JSON graph:\n{pformat(connection_graphs[index])}")
        _logger.debug(f"Initial graph:\n{random_graphs[index]}")
        _logger.debug(f"Modified graph:\n{graph}")
        assert False
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_add_input_simple(test) -> None:
    """Verify adding inputs makes valid graphs.

    Create a random graph, add an input & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(1)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

    before: int = graph.rows[SRC_EP].get("I", 0)
    graph.add_input()
    graph.normalize()
    after: int = graph.rows[SRC_EP].get("I", 0)
    assert after == before + 1
    passed: bool = graph.validate()
    if not passed:
        _logger.debug(f"Initial JSON graph:\n{pformat(connection_graphs[index])}")
        _logger.debug(f"Initial graph:\n{random_graphs[index]}")
        _logger.debug(f"Modified graph:\n{graph}")
        assert False
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_remove_input_simple(test) -> None:
    """Verify removing inputs makes valid graphs.

    Create a random graph, remove an input & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(2)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

    before: int = graph.rows[SRC_EP].get("I", 0)
    graph.remove_input()
    graph.normalize()
    after: int = graph.rows[SRC_EP].get("I", 0)

    # E1001 & E01016 are a legit error when removing an input.
    assert after == before - 1 if before else after == before == 0
    passed: bool = graph.validate()
    if not passed:
        _logger.debug(f"Initial JSON graph:\n{pformat(connection_graphs[index])}")
        _logger.debug(f"Initial graph:\n{random_graphs[index]}")
        _logger.debug(f"Modified graph:\n{graph}")
        codes = set([t.code for t in graph.status])
        codes.discard("E01001")
        codes.discard("E01016")
        assert not codes
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_add_output_simple(test) -> None:
    """Verify adding outputs makes valid graphs.

    Create a random graph, add an output & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(3)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

    before: int = graph.rows[DST_EP].get("O", 0)
    graph.add_output()
    graph.normalize()
    after: int = graph.rows[DST_EP].get("O", 0)
    passed: bool = graph.validate() and after == before + 1
    if not passed:
        _logger.debug(f"Initial JSON graph:\n{pformat(connection_graphs[index])}")
        _logger.debug(f"Initial graph:\n{random_graphs[index]}")
        _logger.debug(f"Modified graph:\n{graph}")
        assert False
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_remove_output_simple(test) -> None:
    """Verify removing outputs makes valid graphs.

    Create a random graph, remove an output & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(4)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

    before: int = graph.rows[DST_EP].get("O", 0)
    graph.remove_output()
    graph.normalize()
    after: int = graph.rows[DST_EP].get("O", 0)

    # E1000 is a legit error when removing an output (no row O).
    passed: bool = graph.validate() and after == before - 1 if before else after == before == 0
    if not passed:
        _logger.debug(f"Initial JSON graph:\n{pformat(connection_graphs[index])}")
        _logger.debug(f"Initial graph:\n{random_graphs[index]}")
        _logger.debug(f"Modified graph:\n{graph}")
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard("E01006")
        assert not codes
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_remove_constant_simple(test) -> None:
    """Verify removing contants makes valid graphs.

    Create a random graph, remove a constant & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(5)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

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


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_binary_compound_modifications(test) -> None:
    """Verify compounding modifications still makes valid graphs.

    Create a random graph, do 2 random modifications & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(6)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

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


@pytest.mark.parametrize("test", range(NUM_TEST_CASES))
def test_nary_compound_modifications(test) -> None:
    """Verify compounding modifications still makes valid graphs.

    Create a random graph, do 3 to 20 random modifications & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    seed(7)
    index: int = randint(0, len(random_graphs) - 1) if NUM_TEST_CASES != len(random_graphs) else test
    _logger.debug(f"Case {test}: Random graph index: {index}")
    graph: gc_graph = random_graphs[index]

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
