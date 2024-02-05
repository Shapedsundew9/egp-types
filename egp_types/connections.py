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
from typing import cast, TYPE_CHECKING
from random import choice
from logging import DEBUG, Logger, NullHandler, getLogger

from numpy import ndarray, uint8, unique, where
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .rows import rows

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
    VALID_ROW_SOURCES,
    VALID_DESTINATIONS
)


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class ConnIdx(IntEnum):
    """Indices for connection definitions."""

    SRC_ROW = 0
    DST_ROW = 1
    SRC_IDX = 2
    DST_IDX = 3

class connections(ndarray):
    """Connections between source and destination rows in a graph."""

    def __init__(self, json_graph: JSONGraph, **kwargs) -> None:
        super().__init__()
        if "rndm" in kwargs:
            self._random(kwargs["rndm"])
        else:
            dst_rows: list[DestinationRow] = cast(list[DestinationRow], sorted(row for row in json_graph.keys() if row != "C"))
            self[ConnIdx.SRC_ROW] = [SOURCE_ROW_INDEXES[cast(SourceRow, ep[CPI.ROW])] for row in dst_rows for ep in json_graph[row]]
            self[ConnIdx.DST_ROW] = [DESTINATION_ROW_INDEXES[row] for row in dst_rows for _ in json_graph[row]]
            self[ConnIdx.SRC_IDX] = [cast(int, ep[CPI.IDX]) for row in dst_rows for ep in json_graph[row]]
            self[ConnIdx.DST_IDX] = [idx for row in dst_rows for idx, _ in enumerate(json_graph[row])]

    def __new__(cls, json_graph: JSONGraph, **kwargs) -> connections:
        """Create a byte array for the connection data"""
        # A valid graph has 1 connection per destination endpoint.
        if "rndm" in kwargs:
            shape: tuple[int, int] = (4, sum(len(kwargs["rndm"][DESTINATION_ROW_INDEXES[row]]) for row in DESTINATION_ROWS))
        else:
            shape: tuple[int, int] = (4, sum(len(val) for row, val in json_graph.items() if row in DESTINATION_ROWS))

        return super().__new__(cls, shape, dtype=uint8)  # pylint: disable=unexpected-keyword-arg

    def __repr__(self) -> str:
        """Return the string representation of the connections."""
        retval: list[str] = [f"Connections instance {id(self)}:"]
        for row_idx in sorted(unique(self[ConnIdx.SRC_ROW])):
            con: NDArray = self.get_src_connections(row_idx)
            cons: NDArray = con[:, con[ConnIdx.SRC_IDX].argsort()]
            retval.append("\tSRC: " + " ".join(f"{ROWS_INDEXED[row]}{idx:03}" for row, idx in zip(cons[ConnIdx.SRC_ROW], cons[ ConnIdx.SRC_IDX])))
            retval.append("\t     " + " ".join(" |  " for _ in cons[ConnIdx.SRC_ROW]))
            retval.append("\tDST: " + " ".join(f"{ROWS_INDEXED[row]}{idx:03}" for row, idx in zip(cons[ConnIdx.DST_ROW], cons[ConnIdx.DST_IDX])))
            retval.append("")
        return "\n".join(retval)

    def get_connections(self, row: Row, cls: EndPointClassStr) -> ndarray:
        """Return the connections where one end matches row and key[1] class (s or d)."""
        sord: ConnIdx = ConnIdx.SRC_ROW if cls == "s" else ConnIdx.DST_ROW
        row_index: SrcRowIndex | DstRowIndex = SOURCE_ROW_INDEXES[row] if cls == "s" else DESTINATION_ROW_INDEXES[row]  # type: ignore
        return self[:, self[sord] == row_index]

    def get_src_connections(self, sri: SrcRowIndex) -> ndarray:
        """Return the connections where the source row matches row."""
        return self[:, self[ConnIdx.SRC_ROW] == sri]

    def get_dst_connections(self, dri) -> ndarray:
        """Return the connections where the destination row matches row."""
        return self[:, self[ConnIdx.DST_ROW] == dri]

    def mermaid(self) -> list[str]:
        """Return the mermaid charts string for the connections."""
        return [f"uid{ROWS_INDEXED[sr]}{si:03}s --> uid{ROWS_INDEXED[dr]}{di:03}d" for sr, dr, si, di in self.T if dr != DstRowIndex.U]

    def _random(self, nrows: rows) -> None:
        """Create a random set of connections."""
        cons: list[list[int]] = [[], [], [], []]
        has_f: bool = nrows.valid(DstRowIndex.F)
        for row in filter(lambda x: x != "U", VALID_DESTINATIONS[has_f]):
            dri: DstRowIndex = DESTINATION_ROW_INDEXES[row]
            if nrows.valid(dri):
                # If the destination row is not empty iterate through the endpoint to create a connection for each
                for idx, ept in enumerate(nrows[dri]):
                    # Find valid source rows with the ept in it
                    sri: SrcRowIndex = choice([SOURCE_ROW_INDEXES[r] for r in VALID_ROW_SOURCES[has_f][row] if ept in nrows[SOURCE_ROW_INDEXES[r]]])
                    # The source row is randomly chosen from the valid sources for the destination row
                    cons[ConnIdx.SRC_ROW].append(sri)
                    # The destination row is known
                    cons[ConnIdx.DST_ROW].append(dri)
                    # Randomly choose an endpoint of the selected type in the source row
                    cons[ConnIdx.SRC_IDX].append(choice(where(nrows[sri] == ept)[0]))
                    # Destination endpoint index is known
                    cons[ConnIdx.DST_IDX].append(idx)
        # Redefine the connections array with the new connections
        self[ConnIdx.SRC_ROW] = cons[ConnIdx.SRC_ROW]
        self[ConnIdx.DST_ROW] = cons[ConnIdx.DST_ROW]
        self[ConnIdx.SRC_IDX] = cons[ConnIdx.SRC_IDX]
        self[ConnIdx.DST_IDX] = cons[ConnIdx.DST_IDX]

    def assertions(self) -> None:
        """Validate assertions for the connections."""
        # Validate source row
        for src_row_index in unique(self[ConnIdx.SRC_ROW]):
            assert src_row_index in SOURCE_ROW_INDEXES.values(), "Source row index {src_row_index} is not valid"
            src_row_indices: NDArray = unique(self[ConnIdx.SRC_IDX][self[ConnIdx.SRC_ROW] == src_row_index])
            assert len(src_row_indices) <= 256, f"Source row {ROWS_INDEXED[src_row_index]} has too many source endpoints"

        # Validate destination row
        for dst_row_index in unique(self[ConnIdx.DST_ROW]):
            assert dst_row_index in DESTINATION_ROW_INDEXES.values(), f"Destination row index {dst_row_index} is not valid"
            dst_row_indices: NDArray = self[ConnIdx.DST_IDX][self[ConnIdx.DST_ROW] == dst_row_index]
            assert len(dst_row_indices) <= 256, f"Destination row {ROWS_INDEXED[dst_row_index]} has too many destination endpoints"
            for idx, dst_idx in enumerate(dst_row_indices):
                assert idx == dst_idx, f"Destination row {ROWS_INDEXED[dst_row_index]} has non-sequential destination endpoint indices:\n{dst_row_indices}"
