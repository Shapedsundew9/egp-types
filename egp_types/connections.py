"""The connections module.

# Connections

The connections class defines all the edges in the genetic code graph. Edges are directed and connect source
interfaces to destination interfaces. The connections class is a 4xN array where N is the number of connections.
The first row is the source row designation index, the second row is the destination row designation index,
the third row is the source row endpoint index and the fourth row is the destination row endpoint index.

This format is efficient in memory usage at the cost of some runtime.
"""
from __future__ import annotations

from enum import IntEnum
from typing import cast

from numpy import ndarray, uint8, unique
from numpy.typing import NDArray

from .egp_typing import (
    CPI,
    DESTINATION_ROW_INDEXES,
    DESTINATION_ROWS,
    Row,
    EndPointClassStr,
    ROWS_INDEXED,
    SOURCE_ROW_INDEXES,
    JSONGraph,
    SourceRow,
    DestinationRow,
    SrcRowIndex,
    DstRowIndex,
)


class ConnIdx(IntEnum):
    """Indices for connection definitions."""

    SRC_ROW = 0
    DST_ROW = 1
    SRC_IDX = 2
    DST_IDX = 3


class connections(ndarray):
    """Connections between source and destination rows in a graph."""

    def __init__(self, *_, **kwargs) -> None:
        super().__init__()
        json_graph: JSONGraph = cast(JSONGraph, kwargs["json_graph"])
        self[ConnIdx.SRC_ROW] = [
            SOURCE_ROW_INDEXES[cast(SourceRow, ep[CPI.ROW])] for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS
        ]
        self[ConnIdx.DST_ROW] = [DESTINATION_ROW_INDEXES[row] for row in json_graph for _ in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.SRC_IDX] = [cast(int, ep[CPI.IDX]) for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.DST_IDX] = [cast(int, ep[CPI.IDX]) for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]

    def __new__(cls, *_, **kwargs) -> connections:
        """Create a byte array for the connection data"""
        shape: tuple[int, int] = (4, sum(len(val) for row, val in kwargs["json_graph"].items() if row in DESTINATION_ROWS))
        return super().__new__(cls, shape, dtype=uint8)  # pylint: disable=unexpected-keyword-arg

    def get_connections(self, row: Row, cls: EndPointClassStr) -> ndarray:
        """Return the connections where one end matches row and key[1] class (s or d)."""
        sord: ConnIdx = ConnIdx.SRC_ROW if cls == "s" else ConnIdx.DST_ROW
        row_index: SrcRowIndex | DstRowIndex = SOURCE_ROW_INDEXES[row] if cls == "s" else DESTINATION_ROW_INDEXES[row]  # type: ignore
        return self[:, self[sord] == row_index]

    def get_src_connections(self, row: SourceRow) -> ndarray:
        """Return the connections where the source row matches row."""
        return self[:, self[ConnIdx.SRC_ROW] == SOURCE_ROW_INDEXES[row]]

    def get_dst_connection(self, row: DestinationRow) -> ndarray:
        """Return the connections where the destination row matches row."""
        return self[:, self[ConnIdx.DST_ROW] == DESTINATION_ROW_INDEXES[row]]

    def mermaid(self) -> list[str]:
        """Return the mermaid charts string for the connections."""
        return [f"uid{ROWS_INDEXED[sr]}{si:03}s --> uid{ROWS_INDEXED[dr]}{di:03}d" for sr, dr, si, di in self.T]

    def assertions(self) -> None:
        """Validate assertions for the connections."""
        # Validate source row
        for src_row_index in unique(self[ConnIdx.SRC_ROW]):
            if src_row_index not in SOURCE_ROW_INDEXES.values():
                raise ValueError(f"Source row index {src_row_index} is not valid")
            src_row_indices: NDArray = unique(self[ConnIdx.SRC_IDX][self[ConnIdx.SRC_ROW] == src_row_index])
            if len(src_row_indices) > 256:
                raise ValueError(f"Source row {ROWS_INDEXED[src_row_index]} has too many source endpoints")
            for idx, src_idx in enumerate(src_row_indices):
                if idx != src_idx:
                    raise ValueError(
                        f"Source row {ROWS_INDEXED[src_row_index]} has non-sequential source endpoint indices:\n{src_row_indices}"
                    )
        # Validate destination row
        for dst_row_index in unique(self[ConnIdx.DST_ROW]):
            if dst_row_index not in DESTINATION_ROW_INDEXES.values():
                raise ValueError(f"Destination row index {dst_row_index} is not valid")
            dst_row_indices: NDArray = unique(self[ConnIdx.DST_IDX][self[ConnIdx.DST_ROW] == dst_row_index])
            if len(dst_row_indices) > 256:
                raise ValueError(f"Destination row {ROWS_INDEXED[dst_row_index]} has too many destination endpoints")
            for idx, dst_idx in enumerate(dst_row_indices):
                if idx != dst_idx:
                    raise ValueError(
                        f"Destination row {ROWS_INDEXED[dst_row_index]} has non-sequential destination endpoint indices:\n{dst_row_indices}"
                    )
