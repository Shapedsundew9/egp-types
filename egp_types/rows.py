"""Classes for the rows of a genetic code application graph."""
from __future__ import annotations

from typing import Generator, cast, TYPE_CHECKING

from numpy import ndarray

from .egp_typing import (CPI, DESTINATION_ROWS, SOURCE_ROWS, ConstantExecStr,
                         DstRowIndex, EndPointType, JSONGraph, SrcRowIndex)
from .interface import (EMPTY_INTERFACE, EMPTY_INTERFACE_C, INTERFACE_F,
                        interface, interface_c)


if TYPE_CHECKING:
    from .genetic_code import _genetic_code


class rows(ndarray):
    """Rows of a genetic code application graph."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        json_graph: JSONGraph = cast(JSONGraph, kwargs["json_graph"])
        gca: _genetic_code = kwargs["gca"]
        gcb: _genetic_code = kwargs["gcb"]
        self[SrcRowIndex.I] = self.i_if_from_graph(json_graph)
        self[SrcRowIndex.C] = self.row_c_from_graph(json_graph)
        self[SrcRowIndex.A] = gca.graph.row[SrcRowIndex.I] if gca is not kwargs["empty"] else EMPTY_INTERFACE
        self[SrcRowIndex.B] = gcb.graph.row[SrcRowIndex.I] if gcb is not kwargs["empty"] else EMPTY_INTERFACE
        self[DstRowIndex.F] = INTERFACE_F if "F" in json_graph else EMPTY_INTERFACE
        self[DstRowIndex.A] = gca.graph.row[DstRowIndex.A] if gca is not kwargs["empty"] else EMPTY_INTERFACE
        self[DstRowIndex.B] = gcb.graph.row[DstRowIndex.B] if gcb is not kwargs["empty"] else EMPTY_INTERFACE
        self[DstRowIndex.O] = (
            interface(cast(EndPointType, src_ep[CPI.TYP]) for src_ep in json_graph["O"])
            if "O" in json_graph and json_graph["O"]
            else EMPTY_INTERFACE
        )

    def __new__(cls, *_, **__) -> rows:
        shape: tuple[int] = (len(SOURCE_ROWS) + len(DESTINATION_ROWS),)
        return super().__new__(cls, shape, dtype=object)  # pylint: disable=unexpected-keyword-arg

    def i_if_from_graph(self, json_graph: JSONGraph) -> interface:
        """Return the I interface for a genetic code application graph."""
        i_srcs: Generator = (dst_ep for dst_eps in json_graph.values() for dst_ep in dst_eps if dst_ep[CPI.ROW] == "I")
        sorted_i_srcs: list[list[EndPointType]] = sorted(i_srcs, key=lambda ep: ep[CPI.IDX])
        if not sorted_i_srcs:
            return EMPTY_INTERFACE
        return interface(cast(EndPointType, ep[CPI.TYP]) for ep in sorted_i_srcs)

    def row_c_from_graph(self, json_graph: JSONGraph) -> interface_c:
        """Return the C source interface for a genetic code application graph."""
        return (
            interface_c(cast(list[list[ConstantExecStr | EndPointType]], json_graph["C"]))
            if "C" in json_graph and json_graph["C"]
            else EMPTY_INTERFACE_C
        )
