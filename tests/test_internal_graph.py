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
                                      random_internal_graph, SrcEndPointDict, DstEndPointDict, EndPointDict, dst_end_point_ref)
from egp_types.reference import reference
from egp_types.egp_typing import VALID_GRAPH_ROW_COMBINATIONS, SRC_EP, DST_EP
import pytest
from egp_types.internal_graph import internal_graph, internal_graph_from_json, random_internal_graph


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


def test_internal_graph_repr() -> None:
    """Test case for internal_graph.__repr__()"""
    graph = internal_graph()
    assert repr(graph) == "internal_graph()"


def test_internal_graph_add() -> None:
    """Test case for internal_graph.add()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    assert len(graph) == 1

# Test case for internal_graph.json_obj()
def test_internal_graph_json_obj() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    json_obj: dict[str, list[str | int | bool | list[list[str | int]] | None]] = graph.json_obj()
    assert isinstance(json_obj, dict)
    assert "A" in json_obj
    assert len(json_obj["A"]) == 1

# Test case for internal_graph.next_idx()
def test_internal_graph_next_idx() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    assert graph.next_idx("A", SRC_EP) == 2

# Test case for internal_graph.cls_filter()
def test_internal_graph_cls_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.cls_filter(SRC_EP))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.dst_filter()
def test_internal_graph_dst_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)

# Test case for internal_graph.src_filter()
def test_internal_graph_src_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.row_filter()
def test_internal_graph_row_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.row_filter("A"))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.row_cls_filter()
def test_internal_graph_row_cls_filter():
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.row_cls_filter("A", SRC_EP))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.rows_filter()
def test_internal_graph_rows_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.rows_filter(["A", "B"]))
    assert len(filtered_eps) == 2

# Test case for internal_graph.dst_row_filter()
def test_internal_graph_dst_row_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_row_filter("B"))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)

# Test case for internal_graph.src_row_filter()
def test_internal_graph_src_row_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_row_filter("A"))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.dst_rows_filter()
def test_internal_graph_dst_rows_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_rows_filter(["B"]))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)

# Test case for internal_graph.src_rows_filter()
def test_internal_graph_src_rows_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_rows_filter(["A"]))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.dst_unref_filter()
def test_internal_graph_dst_unref_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_unref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)

# Test case for internal_graph.src_unref_filter()
def test_internal_graph_src_unref_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_unref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.dst_ref_filter()
def test_internal_graph_dst_ref_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_ref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)

# Test case for internal_graph.src_ref_filter()
def test_internal_graph_src_ref_filter() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_ref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)

# Test case for internal_graph.num_eps()
def test_internal_graph_num_eps() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(src_end_point("A", 1, 2))
    assert graph.num_eps("A", SRC_EP) == 2

# Test case for internal_graph.copy_row()
def test_internal_graph_copy_row() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    copied_row = graph.copy_row("A")
    assert isinstance(copied_row, internal_graph)
    assert len(copied_row) == 1

# Test case for internal_graph.copy_rows()
def test_internal_graph_copy_rows() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    copied_rows = graph.copy_rows(["A", "B"])
    assert isinstance(copied_rows, internal_graph)
    assert len(copied_rows) == 2

# Test case for internal_graph.copy_rows_src_eps()
def test_internal_graph_copy_rows_src_eps() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    copied_rows: SrcEndPointDict = graph.copy_rows_src_eps(["A", "B"])
    assert isinstance(copied_rows, dict)
    assert len(copied_rows) == 1

# Test case for internal_graph.copy_rows_dst_eps()
def test_internal_graph_copy_rows_dst_eps() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    copied_rows = graph.copy_rows_dst_eps(["A", "B"])
    assert isinstance(copied_rows,dict)
    assert len(copied_rows) == 1

# Test case for internal_graph.move_row()
def test_internal_graph_move_row() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    moved_row = graph.move_row("A", "B")
    assert isinstance(moved_row, internal_graph)
    assert len(moved_row) == 2

# Test case for internal_graph.move_row_cls()
def test_internal_graph_move_row_cls() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    moved_row: EndPointDict = graph.move_row_cls("A", SRC_EP, "B", DST_EP)
    assert isinstance(moved_row, internal_graph)
    assert len(moved_row) == 2

# Test case for internal_graph.direct_connect()
def test_internal_graph_direct_connect() -> None:
    graph = internal_graph()
    connected_eps: DstEndPointDict = graph.direct_connect("A", "B")
    assert isinstance(connected_eps, dict)
    assert len(connected_eps) == 1

# Test case for internal_graph.append_connect()
def test_internal_graph_append_connect() -> None:
    graph = internal_graph()
    connected_eps = graph.append_connect("A", "B")
    assert isinstance(connected_eps, dict)
    assert len(connected_eps) == 1

# Test case for internal_graph.redirect_refs()
def test_internal_graph_redirect_refs() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2, refs=[dst_end_point_ref("B", 0)]))
    graph.add(dst_end_point("B", 0, 2))
    graph.redirect_refs("A", SRC_EP, "B", "O")
    assert len(graph) == 2

# Test case for internal_graph.as_row()
def test_internal_graph_as_row() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    row: EndPointDict = graph.as_row("A")
    assert isinstance(row, internal_graph)
    assert len(row) == 1

# Test case for internal_graph.interface_from()
def test_internal_graph_interface_from() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    interface: EndPointDict = graph.interface_from("A")
    assert isinstance(interface, internal_graph)
    assert len(interface) == 1

# Test case for internal_graph.embed()
def test_internal_graph_embed() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    embedded_graph = graph.embed("A", "B")
    assert isinstance(embedded_graph, internal_graph)
    assert len(embedded_graph) == 2

# Test case for internal_graph.complete_references()
def test_internal_graph_complete_references() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.complete_references()
    assert len(graph) == 2

# Test case for internal_graph.remove_all_refs()
def test_internal_graph_remove_all_refs() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.remove_all_refs()
    assert len(graph) == 2

# Test case for internal_graph.remove_row()
def test_internal_graph_remove_row() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.remove_row("A")
    assert len(graph) == 1

# Test case for internal_graph.reindex()
def test_internal_graph_reindex() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.reindex()
    assert len(graph) == 2

# Test case for internal_graph.has_row()
def test_internal_graph_has_row() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    assert graph.has_row("A")
    assert not graph.has_row("B")

# Test case for internal_graph.validate()
def test_internal_graph_validate() -> None:
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    assert graph.validate()

# Test case for internal_graph_from_json()
def test_internal_graph_from_json() -> None:
    json_igraph: dict[str, list[str | int | bool | list[list[str | int]] | None]] = {
        "A000d": [
                "I",
                0,
                2
        ],
        "B000d": [
                "A",
                0,
                2
       ]
    }
    graph: internal_graph = internal_graph_from_json(json_igraph)
    assert isinstance(graph, internal_graph)
    assert len(graph) == 2

# Test case for random_internal_graph()
def test_random_internal_graph() -> None:
    graph: internal_graph = random_internal_graph("AB")
    assert isinstance(graph, internal_graph)
    assert len(graph) == 2

