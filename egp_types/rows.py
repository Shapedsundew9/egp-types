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

from logging import DEBUG, Logger, NullHandler, getLogger
from random import choices, randint, shuffle
from typing import cast

from numpy import array_equal, ndarray

from .common import random_constant_str
from .egp_typing import (
    CPI,
    DESTINATION_ROWS,
    DST_EP_CLS_STR,
    GRAPH_ROW_INDEX_ORDER,
    ROW_CLS_INDEXED,
    SOURCE_ROWS,
    SRC_EP_CLS_STR,
    VALID_ROW_SOURCES,
    DstRowIndex,
    EndPointType,
    JSONGraph,
    Row,
    SrcRowIndex,
)
from .ep_type import ep_type_lookup
from .interface import EMPTY_INTERFACE, EMPTY_INTERFACE_C, INTERFACE_F, interface, interface_c
from ._genetic_code import _genetic_code, EMPTY_GENETIC_CODE


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class rows(ndarray):
    """Rows of a genetic code graph."""

    def __init__(self, json_graph: JSONGraph, **kwargs) -> None:
        """Initialise the rows of a genetic code graph from a JSON graph and GCA & GCB."""
        # empty is always defined as the global empty genetic code instance. It is passed in to avoid circular imports.
        super().__init__()
        gca: _genetic_code = kwargs.get("gca", EMPTY_GENETIC_CODE)
        gcb: _genetic_code = kwargs.get("gcb", EMPTY_GENETIC_CODE)
        self[SrcRowIndex.I] = self.i_from_graph(json_graph)
        self[SrcRowIndex.C] = self.c_from_graph(json_graph)
        self[DstRowIndex.F] = INTERFACE_F if "F" in json_graph else EMPTY_INTERFACE
        self[SrcRowIndex.A], self[DstRowIndex.A] = self.ab_from_graph(json_graph, "A", gca)
        self[SrcRowIndex.B], self[DstRowIndex.B] = self.ab_from_graph(json_graph, "B", gcb)
        self[DstRowIndex.O] = (
            interface([cast(EndPointType, src_ep[CPI.TYP]) for src_ep in json_graph["O"]])
            if "O" in json_graph and json_graph["O"]
            else EMPTY_INTERFACE
        )
        self[DstRowIndex.P] = self[DstRowIndex.O] if "F" in json_graph else EMPTY_INTERFACE
        self[DstRowIndex.U] = (
            interface([cast(EndPointType, src_ep[CPI.TYP]) for src_ep in json_graph["U"]]) if "U" in json_graph else EMPTY_INTERFACE
        )

    def __new__(cls, json_graph: JSONGraph, **kwargs) -> rows:
        """Create the rows of a genetic code graph."""
        # All possible rows are defined in the rows class as this is more efficient than checking for the existence of a row.
        shape: tuple[int] = (len(SOURCE_ROWS) + len(DESTINATION_ROWS),)
        return super().__new__(cls, shape, dtype=object)  # pylint: disable=unexpected-keyword-arg

    def __repr__(self) -> str:
        """Return the string representation of the rows."""
        return "\n".join(f"Row {ROW_CLS_INDEXED[i]}\n" + repr(self[i]) + "\n" for i in GRAPH_ROW_INDEX_ORDER)

    def __eq__(self, __value: object) -> bool:
        """Return True if the rows are equal to the value."""
        if not isinstance(__value, rows):
            return super().__eq__(__value)
        return all(array_equal(self[i], __value[i]) for i in GRAPH_ROW_INDEX_ORDER)

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
        i_srcs: set = {tuple(dst_ep) for dst_eps in json_graph.values() for dst_ep in dst_eps if dst_ep[CPI.ROW] == "I"}
        sorted_i_srcs: list[list[EndPointType]] = sorted(i_srcs, key=lambda ep: ep[CPI.IDX])
        if not sorted_i_srcs:
            return EMPTY_INTERFACE
        return interface([cast(EndPointType, ep[CPI.TYP]) for ep in sorted_i_srcs])

    def c_from_graph(self, json_graph: JSONGraph) -> interface_c:
        """Return the C source interface for a genetic code application graph."""
        return interface_c(*list(zip(*json_graph["C"]))) if "C" in json_graph and json_graph["C"] else EMPTY_INTERFACE_C

    def ab_from_graph(self, json_graph: JSONGraph, row: Row, gcx: _genetic_code) -> tuple[interface, interface]:
        """Return the A or B source and destination interfaces for a genetic code application graph."""
        if gcx is EMPTY_GENETIC_CODE:
            srcs: set = {tuple(dst_ep) for dst_eps in json_graph.values() for dst_ep in dst_eps if dst_ep[CPI.ROW] == row}
            sorted_srcs: list[list[EndPointType]] = sorted(srcs, key=lambda ep: ep[CPI.IDX])
            src_iface: interface = EMPTY_INTERFACE if not sorted_srcs else interface([ep[CPI.TYP] for ep in sorted_srcs])
            dst_iface: interface = (
                EMPTY_INTERFACE if not row in json_graph else interface([cast(EndPointType, ep[CPI.TYP]) for ep in json_graph[row]])
            )
            return src_iface, dst_iface
        return gcx["graph"].rows[SrcRowIndex.I], gcx["graph"].rows[DstRowIndex.O]

    def random(
        self,
        rows_str: str,
        max_eps: int,
        ep_types: tuple[EndPointType, ...],
        io: tuple[interface, interface],
    ) -> None:
        """Randomly generate the rows. Generate rows in the order they provide sources in
        the graph so that the types available for each dependent row are known at generation time.
        If gcx is defined it is used for the I and O interfaces. NOTE: To guarantee a valid graph
        when gcx is defined the O interface should use only types at appear in the I interface.
        """
        has_f: bool = "F" in rows_str
        if io[0] is not EMPTY_INTERFACE:
            self[SrcRowIndex.I] = io[0]
        elif "I" in rows_str:
            # If F is to be defined ensure at least one endpoint has type bool.
            num_eps: int = randint(1, max_eps) if not has_f else randint(1, max_eps - 1)
            bool_type_extension: list[int] = [ep_type_lookup["n2v"]["bool"]] if has_f else []
            self[SrcRowIndex.I] = interface(choices(ep_types, k=num_eps) + bool_type_extension)
        if "C" in rows_str:
            types: list[EndPointType] = choices(ep_types, k=max_eps)
            values: list[str] = [random_constant_str(ept) for ept in types]
            self[SrcRowIndex.C] = interface_c(values=values, types=types)
        if has_f:
            self[DstRowIndex.F] = INTERFACE_F
        valid_types: tuple[EndPointType, ...] = tuple(set(self[SrcRowIndex.I]) | set(self[SrcRowIndex.C]))
        # _logger.debug(f"valid_types: {valid_types}")
        if "A" in rows_str:
            self[SrcRowIndex.A] = interface(choices(ep_types, k=randint(1, max_eps)))
            # Need valid source rows to be present to have a valid destination row.
            if any(row in rows_str for row in VALID_ROW_SOURCES[has_f]["A"]):
                self[DstRowIndex.A] = interface(choices(valid_types, k=randint(1, max_eps)))
            else:
                self[DstRowIndex.A] = EMPTY_INTERFACE
            # If there is no row F row sources are valid for rows B & O
            if not has_f:
                valid_types = tuple(set(valid_types) | set(self[SrcRowIndex.A]))
        if "B" in rows_str:
            # Need valid source rows to be present to have a valid destination row.
            if any(row in rows_str for row in VALID_ROW_SOURCES[has_f]["B"]):
                self[DstRowIndex.B] = interface(choices(valid_types, k=randint(1, max_eps)))
            else:
                self[DstRowIndex.B] = EMPTY_INTERFACE
            if not has_f:
                # If there is no row F row B sources are valid for O
                self[SrcRowIndex.B] = interface(choices(ep_types, k=randint(1, max_eps)))
                valid_types = tuple(set(valid_types) | set(self[SrcRowIndex.B]))
            else:
                # If there is a row F row B sources are valid for P and must have the same
                # types available as for O. Easiest way to do this is just be duplicating
                # the A source interface shuffled.
                self[SrcRowIndex.B] = self[SrcRowIndex.A].copy()
                shuffle(self[SrcRowIndex.B])
        if io[1] is not EMPTY_INTERFACE:
            self[DstRowIndex.O] = io[1]
        elif "O" in rows_str:
            self[DstRowIndex.O] = interface(choices(valid_types, k=randint(1, max_eps)))
        self[DstRowIndex.P] = self[DstRowIndex.O] if has_f else EMPTY_INTERFACE
        self[DstRowIndex.U] = EMPTY_INTERFACE

    def setu(self, row_u_types: list[int]) -> None:
        """Set the row U interface. This is a special use case for random graphs."""
        self[DstRowIndex.U] = interface(row_u_types)

    def valid(self, idx: SrcRowIndex | DstRowIndex) -> bool:
        """Return True if the row is valid."""
        return self[idx] is not EMPTY_INTERFACE if idx != SrcRowIndex.C else self[idx] is not EMPTY_INTERFACE_C

    def get_interface(self, iface: str = "IO") -> tuple[interface, interface]:
        """Return the source and destination interfaces."""
        if iface == "IO":
            return self[SrcRowIndex.I], self[DstRowIndex.O]
        if iface == "A":
            return self[SrcRowIndex.A], self[DstRowIndex.A]
        if iface == "B":
            return self[SrcRowIndex.B], self[DstRowIndex.B]
        assert False, f"Unknown interface {iface}"

    def assertions(self) -> None:
        """Assertions for the rows."""
        # REMINDER: It is valid for a row to exist but have no endpoints i.e. an empty interface.
        if self[DstRowIndex.F] is EMPTY_INTERFACE:
            assert self[DstRowIndex.P] is EMPTY_INTERFACE, "Row P must be empty when row F is empty."
        else:
            assert self[DstRowIndex.P] is self[DstRowIndex.O], "Row P must be the same as row O when F is defined."
