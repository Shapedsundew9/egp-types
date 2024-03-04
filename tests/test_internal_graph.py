"""Test cases for the internal graph module."""
from functools import partial
from itertools import count
from json import dump, load
from logging import DEBUG, INFO, Logger, NullHandler, getLogger
from os.path import dirname, exists, join
from pprint import pformat
from random import choice, seed

import pytest
from tqdm import trange

from egp_types.egp_typing import DST_EP, SRC_EP, VALID_GRAPH_ROW_COMBINATIONS
from egp_types.end_point import dst_end_point, src_end_point
from egp_types.gc_graph import gc_graph
from egp_types.internal_graph import (
    DstEndPointDict,
    EndPointDict,
    SrcEndPointDict,
    dst_end_point_ref,
    internal_graph,
    internal_graph_from_json,
    random_internal_graph,
    src_end_point_ref,
)

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
getLogger("surebrec").setLevel(INFO)
getLogger("eGC").setLevel(INFO)
getLogger("ep_type").setLevel(INFO)


NUM_RANDOM_GRAPHS = 4000
FILENAME: str = join(dirname(__file__), "data/random_internal_graph.json")
COMBOS = tuple(VALID_GRAPH_ROW_COMBINATIONS)
if not exists(FILENAME):
    seed(1)
    with open(FILENAME, "w", encoding="utf-8") as f:
        dump(
            [random_internal_graph(choice(COMBOS), verify=True, rseed=rseed).json_obj() for rseed in trange(NUM_RANDOM_GRAPHS)],
            f,
            indent=4,
            sort_keys=True,
        )

with open(FILENAME, "r", encoding="utf-8") as f:
    RANDOM_GRAPHS: list[internal_graph] = [internal_graph_from_json(json_igraph) for json_igraph in load(f)]


def test_internal_graph_repr() -> None:
    """Test case for internal_graph.__repr__()"""
    graph = internal_graph()
    assert isinstance(repr(graph), str)


def test_internal_graph_add() -> None:
    """Test case for internal_graph.add()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    assert len(graph) == 1


def test_internal_graph_json_obj() -> None:
    """Test case for internal_graph.json_obj()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    json_obj: dict[str, list[str | int | bool | list[list[str | int]] | None]] = graph.json_obj()
    assert isinstance(json_obj, dict)
    assert "A000s" in json_obj
    assert len(json_obj["A000s"]) == 6


def test_internal_graph_next_idx() -> None:
    """Test case for internal_graph.next_idx()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    assert graph.next_idx("A", SRC_EP) == 1


def test_internal_graph_cls_filter() -> None:
    """Test case for internal_graph.cls_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.cls_filter(SRC_EP))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_dst_filter() -> None:
    """Test case for internal_graph.dst_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)


def test_internal_graph_src_filter() -> None:
    """Test case for internal_graph.src_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_row_filter() -> None:
    """Test case for internal_graph.row_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.row_filter("A"))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_row_cls_filter() -> None:
    """Test case for internal_graph.row_cls_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.row_cls_filter("A", SRC_EP))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_rows_filter() -> None:
    """Test case for internal_graph.rows_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.rows_filter(["A", "B"]))
    assert len(filtered_eps) == 2


def test_internal_graph_dst_row_filter() -> None:
    """Test case for internal_graph.dst_row_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_row_filter("B"))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)


def test_internal_graph_src_row_filter() -> None:
    """Test case for internal_graph.src_row_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_row_filter("A"))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_dst_rows_filter() -> None:
    """Test case for internal_graph.dst_rows_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_rows_filter(["B"]))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)


def test_internal_graph_src_rows_filter() -> None:
    """Test case for internal_graph.src_rows_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_rows_filter(["A"]))
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_dst_unref_filter() -> None:
    """Test case for internal_graph.dst_unref_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.dst_unref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)


def test_internal_graph_src_unref_filter() -> None:
    """Test case for internal_graph.src_unref_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    filtered_eps = list(graph.src_unref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_dst_ref_filter() -> None:
    """Test case for internal_graph.dst_ref_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2, refs=[dst_end_point_ref("B", 0)]))
    graph.add(dst_end_point("B", 0, 2, refs=[src_end_point_ref("A", 0)]))
    filtered_eps = list(graph.dst_ref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], dst_end_point)


def test_internal_graph_src_ref_filter() -> None:
    """Test case for internal_graph.src_ref_filter()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2, refs=[dst_end_point_ref("B", 0)]))
    graph.add(dst_end_point("B", 0, 2, refs=[src_end_point_ref("A", 0)]))
    filtered_eps = list(graph.src_ref_filter())
    assert len(filtered_eps) == 1
    assert isinstance(filtered_eps[0], src_end_point)


def test_internal_graph_num_eps() -> None:
    """Test case for internal_graph.num_eps()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(src_end_point("A", 1, 2))
    assert graph.num_eps("A", SRC_EP) == 2


def test_internal_graph_copy_row() -> None:
    """Test case for internal_graph.copy_row()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    copied_row: EndPointDict = graph.copy_row("A")
    assert isinstance(copied_row, dict)
    assert len(copied_row) == 1


def test_internal_graph_copy_rows() -> None:
    """Test case for internal_graph.copy_rows()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    copied_rows: EndPointDict = graph.copy_rows(["A", "B"])
    assert isinstance(copied_rows, dict)
    assert len(copied_rows) == 2


def test_internal_graph_copy_rows_src_eps() -> None:
    """Test case for internal_graph.copy_rows_src_eps()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    copied_rows: SrcEndPointDict = graph.copy_rows_src_eps(["A", "B"])
    assert isinstance(copied_rows, dict)
    assert len(copied_rows) == 1


def test_internal_graph_copy_rows_dst_eps() -> None:
    """Test case for internal_graph.copy_rows_dst_eps()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    copied_rows = graph.copy_rows_dst_eps(["A", "B"])
    assert isinstance(copied_rows, dict)
    assert len(copied_rows) == 1


def test_internal_graph_move_row() -> None:
    """Test case for internal_graph.move_row()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    moved_row: EndPointDict = graph.move_row("A", "B")
    assert isinstance(moved_row, dict)
    assert len(moved_row) == 1
    assert "B000s" in moved_row
    assert "B000d" not in moved_row


def test_internal_graph_direct_connect() -> None:
    """Test case for internal_graph.direct_connect()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(src_end_point("B", 0, 2))
    connected_eps: DstEndPointDict = graph.direct_connect("A", "B")
    assert isinstance(connected_eps, dict)
    assert len(connected_eps) == 1


def test_internal_graph_append_connect() -> None:
    """Test case for internal_graph.append_connect()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    connected_eps: DstEndPointDict = graph.append_connect("A", "B")
    assert isinstance(connected_eps, dict)
    assert len(connected_eps) == 1
    assert "B001d" in connected_eps


def test_internal_graph_redirect_refs() -> None:
    """Test case for internal_graph.redirect_refs()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2, refs=[dst_end_point_ref("B", 0)]))
    graph.add(dst_end_point("B", 0, 2, refs=[src_end_point_ref("A", 0)]))
    graph.redirect_refs("A", SRC_EP, "B", "O")
    assert len(graph) == 2
    assert graph["A000s"].refs[0].row == "O" and graph["A000s"].refs[0].idx == 0


def test_internal_graph_as_row() -> None:
    """Test case for internal_graph.as_row()"""
    graph = internal_graph()
    graph.add(dst_end_point("O", 0, 2))
    graph.add(src_end_point("I", 0, 2))
    row: EndPointDict = graph.as_row("A")
    assert isinstance(row, dict)
    assert len(row) == 2
    assert "A000d" in row
    assert "A000s" in row


def test_internal_graph_remove_all_refs() -> None:
    """Test case for internal_graph.remove_all_refs()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.remove_all_refs()
    assert len(graph) == 2


def test_internal_graph_remove_row() -> None:
    """Test case for internal_graph.remove_row()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.remove_row("A")
    assert len(graph) == 1


def test_internal_graph_reindex() -> None:
    """Test case for internal_graph.reindex()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    graph.reindex()
    assert len(graph) == 2


def test_internal_graph_has_row() -> None:
    """Test case for internal_graph.has_row()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    assert graph.has_row("A")
    assert not graph.has_row("B")


def test_internal_graph_validate() -> None:
    """Test case for internal_graph.validate()"""
    graph = internal_graph()
    graph.add(src_end_point("A", 0, 2))
    graph.add(dst_end_point("B", 0, 2))
    assert graph.validate()


def test_internal_graph_from_json() -> None:
    """Test case for internal_graph_from_json()"""
    json_igraph: dict[str, list[str | int | bool | list[list[str | int]] | None]] = {
        "A000d": ["A", 0, 2, DST_EP, [["I", 0]], None],
        "B000d": ["B", 0, 2, DST_EP, [], None],
    }
    graph: internal_graph = internal_graph_from_json(json_igraph)
    assert isinstance(graph, internal_graph)
    assert len(graph) == 2


def test_random_internal_graph() -> None:
    """Test case for random_internal_graph()"""
    graph: internal_graph = random_internal_graph("AB", max_row_eps=8, row_stablization=True, verify=True)
    assert isinstance(graph, internal_graph)
    assert len(graph) >= 2 and len(graph) <= 16
    assert "A000s" in graph
    assert "A000d" not in graph
    assert "B000s" in graph
    assert "B000d" in graph
    assert "I000s" not in graph
    assert "O000d" not in graph
    assert "C000s" not in graph
    assert "F000d" not in graph
    assert "P000d" not in graph


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
