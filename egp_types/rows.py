"""The rows module.

# Rows

A row is a concept in the genetic code graph. It is one base interface instance or one or both
of a src_interface and a dst_interface instance determined by its letter designation e.g. A, B, F, O, P, U...
See egp_typing ROWS for the full list of row designations.

Rows are linked by directed edges, called connections, between source and destination interfaces.
See connections module for more information.

Whilst every genetic code graph may not have all possible rows it is efficient to define all possible rows
in the rows class. Unused rows are set to the global empty interface instance.
"""
from __future__ import annotations

from typing import Generator, cast, TYPE_CHECKING

from numpy import ndarray

from .egp_typing import (CPI, DESTINATION_ROWS, SOURCE_ROWS, Row,
                         DstRowIndex, EndPointType, JSONGraph, SrcRowIndex, SRC_EP_CLS_STR, DST_EP_CLS_STR)
from .interface import (EMPTY_INTERFACE, EMPTY_INTERFACE_C, INTERFACE_F,
                        interface, interface_c)


if TYPE_CHECKING:
    from .genetic_code import _genetic_code


class rows(ndarray):
    """Rows of a genetic code graph."""

    def __init__(self, json_graph: JSONGraph, gca: _genetic_code, gcb: _genetic_code, empty: _genetic_code) -> None:
        """Initialise the rows of a genetic code graph from a JSON graph and GCA & GCB."""
        # empty is always defined as the global empty genetic code instance. It is passed in to avoid circular imports.
        super().__init__()
        self[SrcRowIndex.I] = self.i_from_graph(json_graph)
        self[SrcRowIndex.C] = self.c_from_graph(json_graph)
        self[DstRowIndex.F] = INTERFACE_F if "F" in json_graph else EMPTY_INTERFACE
        self[SrcRowIndex.A], self[DstRowIndex.A] = self.ab_from_graph(json_graph, "A", gca, empty)
        self[SrcRowIndex.B], self[DstRowIndex.B] = self.ab_from_graph(json_graph, "B", gcb, empty)
        self[DstRowIndex.O] = (
            interface([cast(EndPointType, src_ep[CPI.TYP]) for src_ep in json_graph["O"]])
            if "O" in json_graph and json_graph["O"]
            else EMPTY_INTERFACE
        )

    def __new__(cls, json_graph: JSONGraph, gca: _genetic_code, gcb: _genetic_code, empty: _genetic_code) -> rows:
        """Create the rows of a genetic code graph."""
        # All possible rows are defined in the rows class as this is more efficient than checking for the existence of a row.
        shape: tuple[int] = (len(SOURCE_ROWS) + len(DESTINATION_ROWS),)
        return super().__new__(cls, shape, dtype=object)  # pylint: disable=unexpected-keyword-arg

    def mermaid(self) -> list[str]:
        """Return the mermaid charts string for the rows."""
        retval: list[str] = []
        if self[SrcRowIndex.I] is not EMPTY_INTERFACE:
            retval += ["subgraph uidI", "\tdirection TB"] + ["\t" + s for s in self[SrcRowIndex.I].mermaid("I", SRC_EP_CLS_STR)] + ["end"]
        if self[SrcRowIndex.C] is not EMPTY_INTERFACE_C:
            retval += ["subgraph uidC", "\tdirection TB"] + ["\t" + s for s in self[SrcRowIndex.C].mermaid("C", SRC_EP_CLS_STR)] + ["end"]
        if self[DstRowIndex.F] is not EMPTY_INTERFACE:
            retval += ["subgraph uidF", "\tdirection TB"] + ["\t" + s for s in self[DstRowIndex.F].mermaid("F", DST_EP_CLS_STR)] + ["end"]
        if self[SrcRowIndex.A] is not EMPTY_INTERFACE:
            retval += ["subgraph uidA", "\tdirection TB"] + ["\t" + s for s in self[SrcRowIndex.A].mermaid("A", SRC_EP_CLS_STR)]
            if self[DstRowIndex.A] is not EMPTY_INTERFACE:
                retval += ["\t" + s for s in self[DstRowIndex.A].mermaid("A", DST_EP_CLS_STR)]
            retval += ["end"]
        if self[SrcRowIndex.B] is not EMPTY_INTERFACE:
            retval += ["subgraph uidB", "\tdirection TB"] + ["\t" + s for s in self[SrcRowIndex.B].mermaid("B", SRC_EP_CLS_STR)]
            if self[DstRowIndex.B] is not EMPTY_INTERFACE:
                retval += ["\t" + s for s in self[DstRowIndex.B].mermaid("B", DST_EP_CLS_STR)]
            retval += ["end"]
        if self[DstRowIndex.O] is not EMPTY_INTERFACE:
            retval += ["subgraph uidO", "\tdirection TB"] + ["\t" + s for s in self[DstRowIndex.O].mermaid("O", DST_EP_CLS_STR)] + ["end"]
        if self[DstRowIndex.P] is not EMPTY_INTERFACE:
            retval += ["subgraph uidP", "\tdirection TB"] + ["\t" + s for s in self[DstRowIndex.P].mermaid("P", DST_EP_CLS_STR)] + ["end"]
        return retval

    def i_from_graph(self, json_graph: JSONGraph) -> interface:
        """Return the I interface for a genetic code application graph."""
        i_srcs: Generator = (dst_ep for dst_eps in json_graph.values() for dst_ep in dst_eps if dst_ep[CPI.ROW] == "I")
        sorted_i_srcs: list[list[EndPointType]] = sorted(i_srcs, key=lambda ep: ep[CPI.IDX])
        if not sorted_i_srcs:
            return EMPTY_INTERFACE
        return interface([cast(EndPointType, ep[CPI.TYP]) for ep in sorted_i_srcs])

    def c_from_graph(self, json_graph: JSONGraph) -> interface_c:
        """Return the C source interface for a genetic code application graph."""
        return interface_c(*list(zip(*json_graph["C"]))) if "C" in json_graph and json_graph["C"] else EMPTY_INTERFACE_C

    def ab_from_graph(self, json_graph: JSONGraph, row: Row, gcx: _genetic_code, empty: _genetic_code) -> tuple[interface, interface]:
        """Return the A or B source and destination interfaces for a genetic code application graph."""
        if gcx is empty:
            srcs: Generator = (dst_ep for dst_eps in json_graph.values() for dst_ep in dst_eps if dst_ep[CPI.ROW] == row)
            sorted_srcs: list[list[EndPointType]] = sorted(srcs, key=lambda ep: ep[CPI.IDX])
            src_iface: interface = EMPTY_INTERFACE if not sorted_srcs else interface([ep[CPI.TYP] for ep in sorted_srcs])
            dst_iface: interface = EMPTY_INTERFACE if not row in json_graph else interface([cast(EndPointType, ep[CPI.TYP]) for ep in json_graph[row]])
            return src_iface, dst_iface
        return gcx.graph.rows[SrcRowIndex.I], gcx.graph.rows[DstRowIndex.O]
