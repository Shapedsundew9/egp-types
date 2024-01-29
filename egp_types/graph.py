"""Graph class for genetic code application graphs.

# Graph

A graph is an internal representation of the JSONGraph stored in the GMS.
A graph is made up of rows and connections between them according to some rules.
A row contains a row identifier (class member) and neither, one or both
of a source interface and a destination interface (see row class).
An interface is a list of endpoints (see interface class).
Connections are made between endpoints of different rows according to rules.
The most fundamental rules are that the endpoints on the connected rows must be of
the same type and that connections are directional: Source --> Destination.
"""

from egp_types.egp_typing import JSONGraph, SourceRow, DestinationRow, EndPointType, ConstantExecStr, CPI
from egp_types.interface import interface


class _graph():

    def __init__(self, graph: JSONGraph) -> None:
        pass

    def src_ifs(self, row: SourceRow) -> interface:
        """Return the source interface for the specified row."""
        if isinstance(self, graph):
            _genetic_code.data_store.access_sequence[self.idx] = next(_genetic_code.access_number)
            return self._src_ifs[SOURCE_ROW_INDEXES[row]]
        return EMPTY_INTERFACE

    def dst_ifs(self, row: DestinationRow) -> interface:
        """Return the destination interface for the specified row."""
        if isinstance(self, genetic_code):
            _genetic_code.data_store.access_sequence[self.idx] = next(_genetic_code.access_number)
            return self._dst_ifs[DESTINATION_ROW_INDEXES[row]]
        return EMPTY_INTERFACE

    def src_ifs_from_graph(self, graph: JSONGraph) -> list[interface]:
        """Return the source interfaces for a genetic code application graph."""
        # Make no assumption about the number of source interfaces or their indices
        src_ifs: list[interface] = list(EMPTY_INTERFACE for _ in SOURCE_ROWS)
        src_ifs[SOURCE_ROW_INDEXES["I"]] = self.i_if_from_graph(graph)
        src_ifs[SOURCE_ROW_INDEXES["C"]] = self.row_c_from_graph(graph)
        src_ifs[SOURCE_ROW_INDEXES["A"]] = self.gca.src_ifs("I")
        src_ifs[SOURCE_ROW_INDEXES["B"]] = self.gcb.src_ifs("I")
        return src_ifs

    def i_if_from_graph(self, graph: JSONGraph) -> interface:
        """Return the I interface for a genetic code application graph."""
        i_srcs: Generator = (dst_ep for dst_eps in graph.values() for dst_ep in dst_eps if dst_ep[CPI.ROW] == "I")
        sorted_i_srcs: list[list[EndPointType]] = sorted(i_srcs, key=lambda ep: ep[CPI.IDX])
        if not sorted_i_srcs:
            return EMPTY_INTERFACE
        return interface(cast(EndPointType, ep[CPI.TYP]) for ep in sorted_i_srcs)

    def row_c_from_graph(self, graph: JSONGraph) -> row_c:
        """Return the C source interface for a genetic code application graph."""
        return row_c(cast(list[list[ConstantExecStr | EndPointType]], graph["C"])) if "C" in graph and graph["C"] else EMPTY_ROW_C

    def dst_ifs_from_graph(self, graph: JSONGraph) -> list[interface]:
        """Return the destination interfaces for a genetic code application graph."""
        # Make no assumption about the number of destination interfaces or their indices
        dst_ifs: list[interface] = list(EMPTY_INTERFACE for _ in DESTINATION_ROWS)
        dst_ifs[DESTINATION_ROW_INDEXES["F"]] = ROW_F if "F" in graph else EMPTY_INTERFACE
        dst_ifs[DESTINATION_ROW_INDEXES["A"]] = self.gca.dst_ifs("A")
        dst_ifs[DESTINATION_ROW_INDEXES["B"]] = self.gcb.dst_ifs("B")
        dst_ifs[DESTINATION_ROW_INDEXES["O"]] = (
            interface(cast(EndPointType, src_ep[CPI.TYP]) for src_ep in graph["O"]) if "O" in graph and graph["O"] else EMPTY_INTERFACE
        )
        dst_ifs[DESTINATION_ROW_INDEXES["P"]] = dst_ifs[DESTINATION_ROW_INDEXES["O"]]
        return dst_ifs


class graph(_graph):

    def __init__(self, graph: JSONGraph) -> None:
        self._src_ifs: list[interface] = self.src_ifs_from_graph(gc_dict.get("graph", {}))
        self._dst_ifs: list[interface] = self.dst_ifs_from_graph(gc_dict.get("graph", {}))


