"""Connection data type for the EGP."""
from __future__ import annotations

from enum import IntEnum
from typing import cast

from numpy import ndarray, uint8

from .egp_typing import (CPI, DESTINATION_ROW_INDEXES, DESTINATION_ROWS,
                         SOURCE_ROW_INDEXES, JSONGraph, SourceRow)


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
        self[ConnIdx.DST_ROW] = [DESTINATION_ROW_INDEXES[row] for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.SRC_IDX] = [cast(int, ep[CPI.IDX]) for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.DST_IDX] = [cast(int, ep[CPI.IDX]) for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]

    def __new__(cls, *_, **kwargs) -> connections:
        """Create a byte array for the connection data"""
        shape: tuple[int, int] = (4, sum(len(val) for row, val in kwargs["json_graph"].items() if row in DESTINATION_ROWS))
        return super().__new__(cls, shape, dtype=uint8)  # pylint: disable=unexpected-keyword-arg
