"""gc_graph verficiation."""

from copy import deepcopy
from json import load
from logging import DEBUG, Logger, NullHandler, getLogger
from os.path import dirname, join
from random import randint, random
from typing import Any
from itertools import count
from functools import partial

import pytest
from numpy.random import choice
from surebrec.surebrec import generate

from egp_types.egp_typing import DST_EP, SRC_EP, ConnectionGraph, json_to_connection_graph, ConstantRow
from egp_types.ep_type import EP_TYPE_VALUES, INVALID_EP_TYPE_VALUE, asint, ep_type_lookup, inst
from egp_types.gc_graph import gc_graph
from egp_types.xgc_validator import LGC_entry_validator
from egp_types import set_reference_generator, reference


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
_TEST_RESULTS_JSON = 'data/test_gc_graph_results.json'


# Reference generation for eGC's
ref_generator = partial(reference, owner_id=0, counter=count())
set_reference_generator(ref_generator)


# JSON cannot represent the ConnectionGraph type so a conversion step is needed.
with open(join(dirname(__file__), _TEST_RESULTS_JSON), 'r', encoding='utf-8') as results_file:
    results: list[dict[str, Any]] = load(results_file)
for result in results:
    result['graph'] = json_to_connection_graph(result['graph'])


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
    return asint('builtins_int')


def random_graph() -> gc_graph:
    """Create a random graph.

    The graph is not guaranteed to be valid when p > 0.0. If a destination row requires a type that
    is not present in any valid source row the graph cannot be normalized.

    Args
    ----
    probability: 0.0 <= p <= 1.0 probability of choosing a random type on each type selection.
    """
    rc_graph: ConnectionGraph = json_to_connection_graph(generate(LGC_entry_validator, 1)[0]['graph'])  # type: ignore
    if 'F' in rc_graph:
        # O references A and P reference B - to validate they must have the same types. Easiest to duplicate.
        if 'A' in rc_graph:
            rc_graph['B'] = deepcopy(rc_graph['A'])
        if 'O' in rc_graph:
            # P is the same as O when F is defined.
            rc_graph['P'] = deepcopy(rc_graph['O'])
        elif 'P' in rc_graph:
            # But if there is no O there must be no P
            del rc_graph['P']

    new_constants: ConstantRow = [(ep_type_lookup['instanciation'][typ][inst.DEFAULT.value], typ) for _, typ in rc_graph.get('C', [])]
    if new_constants:
        rc_graph['C'] = new_constants
    gcg = gc_graph(rc_graph)
    if _LOG_DEBUG:
        _logger.debug(f"Pre-normalized randomly generated internal graph:\n{gcg}")
    print("\n", gcg)
    gcg.remove_all_connections()
    print("\nRemoved all connections\n", gcg)
    gcg.purge_unconnectable_types()
    print("\nPurged\n", gcg)
    gcg.reindex()
    print("\nReindexed\n", gcg)
    gcg.normalize()
    return gcg


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_validation(i, case) -> None:
    """Verification the validate() method correctly functions."""
    gcg = gc_graph(case['graph'])
    assert i == case['i']
    assert case['valid'] == gcg.validate()
    if not case['valid']:
        assert all([e in [g.code for g in gcg.status] for e in case['errors']])


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_str(i, case) -> None:
    """Verification the __repr__() method is not broken."""
    gcg = gc_graph(case['graph'])
    assert str(gcg)


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_draw(i, case) -> None:
    """Verification the draw() method is not broken."""
    gcg = gc_graph(case['graph'])
    if case['valid']:
        gcg.draw(join(dirname(__file__), '../logs/gc_graph_' + str(i)))


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_internal(i, case) -> None:
    """Verification initializing with an internal representation is self consistent."""
    gcg = gc_graph(case['graph'])
    _logger.debug(f'Case {i}')
    assert gcg.connection_graph() == gc_graph(i_graph=deepcopy(gcg.i_graph)).connection_graph()


@pytest.mark.parametrize("i, case", enumerate(results))
def test_graph_conversion(i, case) -> None:
    """Verification that converting to internal format and back again is the identity operation."""
    gcg = gc_graph(case['graph'])
    assert i == case['i']
    if case['valid']:
        assert case['graph'] == gcg.connection_graph()


@pytest.mark.parametrize("test", range(100))
def test_remove_connection_simple(test) -> None:
    """Verify adding connections makes valid graphs.

    Create a random graph remove some connections & re-normalise.
    To keep it simple all the endpoints -> None have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    _logger.debug(f'Case {test}')
    graph: gc_graph = random_graph()
    assert graph.validate()

    # TOD: gc_graphO: Split this out into its own test case when the graphs are staticly defined in a JSON file.
    for _ in range(int(sum(graph.rows[DST_EP].values()) / 2)):
        graph.random_remove_connection()
    graph.normalize()
    assert graph.validate()
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(100))
def test_add_connection(test) -> None:
    """Verify adding connections makes valid graphs.

    In this version multiple types endpoint types are used. This can lead to a legitimate invalid
    graph with error codes E01001 or E01004.
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    _logger.debug(f'Case {test}')
    gc: gc_graph = random_graph(0.5)
    if not gc.validate():
        codes = set([t.code for t in gc.status])
        codes.discard('E01001')
        codes.discard('E01004')
        assert not codes


@pytest.mark.parametrize("test", range(100))
def test_stack_simple(test):
    """Verify stacking valid graphs.

    Create two random graphs, gA & gB, and stack them.
    If gB has no inputs it cannot be stacked and the stacking method returns None.
    To keep it simple all the endpoints have the same type ("int"). This
    ensures all validation criteria will be met.
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    global none_limit
    if not test:
        none_limit = 5000

    gA = random_graph()
    gB = random_graph()
    gC = gA.stack(gB)

    if gC is None:
        none_limit -= 1
    assert none_limit
    assert gC is None or gC.validate()
    # if not gC is None:
    #    print(gA)
    #    gA.draw('gA')
    #    print(gB)
    #    gB.draw('gB')
    #    print(gC)
    #    gC.draw('gC')
    #    barf()


@pytest.mark.parametrize("test", range(100))
def test_stack(test):
    """Verify stacking valid graphs.

    Create two random graphs, gA & gB, and stack them.
    If gB has no inputs it cannot be stacked and the stacking method returns None.
    In this version multiple types endpoint types are used. This can lead to a legitimate invalid
    stacked graphs which also return as None.
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    global none_limit
    if not test:
        none_limit = 500

    gA = random_graph(0.5)
    gB = random_graph(0.5)
    gC = gA.stack(gB)

    if gC is None:
        none_limit -= 1
    assert none_limit
    assert gC is None or gC.validate()
    # if not gC is None:
    #    print(gA)
    #    gA.draw('gA')
    #    print(gB)
    #    gB.draw('gB')
    #    print(gC)
    #    gC.draw('gC')
    #    barf()


@pytest.mark.parametrize("test", range(100))
def test_add_input_simple(test):
    """Verify adding inputs makes valid graphs.

    Create a random graph, add an input & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    before = graph.rows[SRC_EP]['I']
    graph.add_input()
    graph.normalize()
    after = graph.rows[SRC_EP]['I']
    assert graph.validate()
    assert after == before + 1
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(100))
def test_remove_input_simple(test):
    """Verify removing inputs makes valid graphs.

    Create a random graph, remove an input & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    before = graph.rows[SRC_EP]['I']
    graph.remove_input()
    graph.normalize()
    after = graph.rows[SRC_EP]['I']

    # E1001 & E01016 are a legit error when removing an input.
    if not graph.validate():
        codes = set([t.code for t in graph.status])
        codes.discard('E01001')
        codes.discard('E01016')
        assert not codes
    assert after == before - 1 if before else after == before == 0
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(100))
def test_add_output_simple(test):
    """Verify adding outputs makes valid graphs.

    Create a random graph, add an output & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    before = graph.rows[DST_EP]['O']
    graph.add_output(asint('builtins_int'))
    graph.normalize()
    after = graph.rows[DST_EP]['O']
    assert graph.validate()
    assert after == before + 1
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(100))
def test_remove_output_simple(test):
    """Verify removing outputs makes valid graphs.

    Create a random graph, remove an output & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    before = graph.rows[DST_EP]['O']
    graph.remove_output()
    graph.normalize()
    after = graph.rows[DST_EP]['O']

    # E1000 is a legit error when removing an output (no row O).
    if not graph.validate():
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard('E01006')
        assert not codes
    if before:
        assert after == before - 1
    else:
        assert after == before == 0
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(100))
def test_remove_constant_simple(test):
    """Verify removing contants makes valid graphs.

    Create a random graph, remove a constant & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    before = len(graph.app_graph.get('C', []))
    graph.remove_constant()
    graph.normalize()
    after = len(graph.app_graph.get('C', []))

    # E1001 is a legit error when removing an constant.
    if not graph.validate():
        codes = set([t.code for t in graph.status])
        codes.discard('E01001')
        assert not codes
    assert after == before - 1 if before else after == before == 0
    # graph.draw(join(_log_location, 'graph_' + str(test)))


@pytest.mark.parametrize("test", range(100))
def test_binary_compound_modifications(test):
    """Verify compounding modifications still makes valid graphs.

    Create a random graph, do 2 random modifications & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    for _ in range(2):
        a = randint(0, 4)
        if a == 0:
            graph.add_input()
        elif a == 1:
            graph.remove_input()
        elif a == 2:
            graph.add_output(asint('builtins_int'))
        elif a == 3:
            graph.remove_output()
        elif a == 4:
            graph.remove_constant()

    # E1000 & E1001 are legit errors when modifiying the graph
    graph.normalize()
    if not graph.validate():
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard('E01006')
        codes.discard('E01001')
        codes.discard('E01016')
        assert not codes


@pytest.mark.parametrize("test", range(100))
def test_nary_compound_modifications(test):
    """Verify compounding modifications still makes valid graphs.

    Create a random graph, do 3 to 20 random modifications & re-normalise.
    To keep it simple all the endpoints have the same type ("int").
    """
    # TODO: These random test cases need to be made static when we are confident in them.
    # Generate them into a JSON file.
    graph = random_graph()
    assert graph.validate()

    for _ in range(randint(3, 20)):
        a = randint(0, 4)
        if a == 0:
            graph.add_input()
        elif a == 1:
            graph.remove_input()
        elif a == 2:
            graph.add_output(asint('builtins_int'))
        elif a == 3:
            graph.remove_output()
        elif a == 4:
            graph.remove_constant()

    # E1000 & E1001 are legit errors when modifiying the graph
    graph.normalize()
    if not graph.validate():
        codes = set([t.code for t in graph.status])

        # E1006 (F with no P) can occur
        codes.discard('E01006')
        codes.discard('E01016')
        codes.discard('E01001')
        assert not codes
