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
from random import choices, randint, shuffle

from numpy import ndarray

from .egp_typing import (
    CPI,
    DESTINATION_ROWS,
    SOURCE_ROWS,
    Row,
    ROW_CLS_INDEXED,
    GRAPH_ROW_INDEX_ORDER,
    DstRowIndex,
    EndPointType,
    JSONGraph,
    SrcRowIndex,
    SRC_EP_CLS_STR,
    DST_EP_CLS_STR,
)
from .interface import EMPTY_INTERFACE, EMPTY_INTERFACE_C, INTERFACE_F, interface, interface_c
from .common import random_constant_str
from .ep_type import ep_type_lookup


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
        self[DstRowIndex.P] = self[DstRowIndex.O]
        self[DstRowIndex.U] = (
            interface([cast(EndPointType, src_ep[CPI.TYP]) for src_ep in json_graph["U"]]) if "U" in json_graph else EMPTY_INTERFACE
        )

    def __new__(cls, json_graph: JSONGraph, gca: _genetic_code, gcb: _genetic_code, empty: _genetic_code) -> rows:
        """Create the rows of a genetic code graph."""
        # All possible rows are defined in the rows class as this is more efficient than checking for the existence of a row.
        shape: tuple[int] = (len(SOURCE_ROWS) + len(DESTINATION_ROWS),)
        return super().__new__(cls, shape, dtype=object)  # pylint: disable=unexpected-keyword-arg

    def __repr__(self) -> str:
        """Return the string representation of the rows."""
        return "\n".join(f"Row {ROW_CLS_INDEXED[i]}\n" + repr(self[i]) + "\n" for i in GRAPH_ROW_INDEX_ORDER)

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
            dst_iface: interface = (
                EMPTY_INTERFACE if not row in json_graph else interface([cast(EndPointType, ep[CPI.TYP]) for ep in json_graph[row]])
            )
            return src_iface, dst_iface
        return gcx.graph.rows[SrcRowIndex.I], gcx.graph.rows[DstRowIndex.O]

    def random(self, rows_str:str, max_eps: int, ep_types: tuple[EndPointType, ...]) -> None:
        """Randomly generate the rows. Generate rows in the order they provide sources in
        the graph so that the types available for each dependent row are known at generation time."""
        if "I" in rows_str:
            # If F is to be defined ensure at least one endpoint has type bool.
            num_eps: int = randint(1, max_eps) if "F" not in rows_str else randint(1, max_eps - 1)
            bool_type_extension: list[int] = [ep_type_lookup["n2v"]["bool"]] if "F" in rows_str else []
            self[SrcRowIndex.I] = interface(choices(ep_types, k=num_eps) + bool_type_extension)
        if "C" in rows_str:

            types: list[EndPointType] = choices(ep_types, k=max_eps)
            values: list[str] = [random_constant_str(ept) for ept in types]
            self[SrcRowIndex.C] = interface_c(values=values, types=types)
        if "F" in rows_str:
            self[DstRowIndex.F] = INTERFACE_F
        valid_types: tuple[EndPointType, ...] = tuple(set(self[SrcRowIndex.I]) & set(self[SrcRowIndex.C]))
        if "A" in rows_str:
            self[SrcRowIndex.A] = interface(choices(valid_types, k=randint(1, max_eps)))
            self[DstRowIndex.A] = interface(choices(ep_types, k=randint(1, max_eps)))
            # If there is no row F row sources are valid for rows B & O
            if "F" not in rows_str:
                valid_types = tuple(set(valid_types) & set(self[SrcRowIndex.A]))
        if "B" in rows_str:
            self[SrcRowIndex.B] = interface(choices(valid_types, k=randint(1, max_eps)))
            if "F" not in rows_str:
                # If there is no row F row B sources are valid for O
                self[DstRowIndex.B] = interface(choices(ep_types, k=randint(1, max_eps)))
                valid_types = tuple(set(valid_types) & set(self[SrcRowIndex.B]))
            else:
                # If there is a row F row B sources are valid for P and must have the same
                # types available as for O. Easiest way to do this is just be duplicating
                # the A source interface shuffled.
                self[SrcRowIndex.B] = self[SrcRowIndex.A].copy()
                shuffle(self[SrcRowIndex.B])
        if "O" in rows_str:
            self[DstRowIndex.O] = interface(choices(valid_types, k=randint(1, max_eps)))
        self[DstRowIndex.P] = self[DstRowIndex.O]
        self[DstRowIndex.U] = EMPTY_INTERFACE

    def valid(self, idx: SrcRowIndex | DstRowIndex) -> bool:
        """Return True if the row is valid."""
        return self[idx] is not EMPTY_INTERFACE
    
    def assertions(self) -> None:
        """Assertions for the rows."""
        # REMINDER: It is valid for a row to exist but have no endpoints i.e. an empty interface.
        if self[DstRowIndex.F] is EMPTY_INTERFACE:
            assert self[DstRowIndex.P] is EMPTY_INTERFACE, "Row P must be empty when row F is empty."
        else:
            assert self[DstRowIndex.P] is self[DstRowIndex.O], "Row P must be the same as row O when F is defined."
