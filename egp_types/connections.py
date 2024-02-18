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
from logging import DEBUG, Logger, NullHandler, getLogger
from random import choice
from typing import TYPE_CHECKING, cast

from numpy import array, array_equal, ndarray, uint8, unique, where
from numpy.typing import NDArray

from .egp_typing import (
    CPI,
    DESTINATION_ROW_INDEXES,
    DESTINATION_ROW_LETTERS,
    DESTINATION_ROWS,
    ROWS_INDEXED,
    SOURCE_ROW_INDEXES,
    VALID_DESTINATIONS,
    VALID_ROW_SOURCES,
    DstRowIndex,
    EndPointClassStr,
    JSONGraph,
    Row,
    SourceRow,
    SrcRowIndex,
)


if TYPE_CHECKING:
    from .rows import rows


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
    # NOTE: There is a 112 byte overhead for a numpy array. For 8 bit integers this is about the
    # same as a list with 1 ints (80 + 28 = 108). Therefore it is efficient in almost all scenarios.
    # However, it is still a lot of overhead for an interface that typically consists of only a few
    # values. e.g. 16 connections = 112 + 1 * 4 * 16 = 176 bytes. 175% overhead.
    # A more efficient implementation (in memory) would be to use a dynamic_store with a contiguous
    # indexed numpy array. This would be a lot of work and
    # complexity but, if the typical connections, has 16 a saving of 112MB on a 2**20 
    # (1 million) entry Gene Pool Cache could be made.
    # The base implmentation could be shared with the interface class. 

    def __init__(self, json_graph: JSONGraph, **kwargs) -> None:
        super().__init__()
        if "_rndm" in kwargs:
            # Randomly generated connections
            # It is not possible to know how many connections will be needed without generating them.
            # kwargs['rndm'] is defined in __new__()
            self[ConnIdx.SRC_ROW] = kwargs["_rndm"][ConnIdx.SRC_ROW]
            self[ConnIdx.DST_ROW] = kwargs["_rndm"][ConnIdx.DST_ROW]
            self[ConnIdx.SRC_IDX] = kwargs["_rndm"][ConnIdx.SRC_IDX]
            self[ConnIdx.DST_IDX] = kwargs["_rndm"][ConnIdx.DST_IDX]
        else:
            dst_rows: list[DstRowIndex] = sorted(DESTINATION_ROW_INDEXES[row] for row in json_graph if row != "C")
            self[ConnIdx.SRC_ROW] = [
                SOURCE_ROW_INDEXES[cast(SourceRow, ep[CPI.ROW])] for sri in dst_rows for ep in json_graph[DESTINATION_ROW_LETTERS[sri]]
            ]
            self[ConnIdx.DST_ROW] = [dri for dri in dst_rows for _ in json_graph[DESTINATION_ROW_LETTERS[dri]]]
            self[ConnIdx.SRC_IDX] = [cast(int, ep[CPI.IDX]) for sri in dst_rows for ep in json_graph[DESTINATION_ROW_LETTERS[sri]]]
            self[ConnIdx.DST_IDX] = [idx for dri in dst_rows for idx, _ in enumerate(json_graph[DESTINATION_ROW_LETTERS[dri]])]

    def __new__(cls, json_graph: JSONGraph, **kwargs) -> connections:
        """Create a byte array for the connection data"""
        # A valid graph has 1 connection per destination endpoint.
        if "_rndm" in kwargs:
            # In a random graph there is no row U until the connections are defined.
            # Rows are passed in as the 1st element of the _rndm list.
            cons: list[list[int]] = cls._random(kwargs["_rndm"][0])
            del kwargs["_rndm"][0]
            kwargs["_rndm"].extend(cons)
            shape: tuple[int, int] = (4, len(cons[ConnIdx.SRC_ROW]))
        else:
            # The connection graph is defined by the number of destination endpoints including row U
            shape: tuple[int, int] = (4, sum(len(val) for row, val in json_graph.items() if row in DESTINATION_ROWS))

        return super().__new__(cls, shape, dtype=uint8)  # pylint: disable=unexpected-keyword-arg

    def __repr__(self) -> str:
        """Return the string representation of the connections."""
        retval: list[str] = [f"Connections instance {id(self)}:"]
        for row_idx in sorted(unique(self[ConnIdx.SRC_ROW])):
            con: NDArray = self.get_src_connections(row_idx)
            cons: NDArray = con[:, con[ConnIdx.SRC_IDX].argsort()]
            retval.append(
                "\tSRC: " + " ".join(f"{ROWS_INDEXED[row]}{idx:03}" for row, idx in zip(cons[ConnIdx.SRC_ROW], cons[ConnIdx.SRC_IDX]))
            )
            retval.append("\t     " + " ".join(" |  " for _ in cons[ConnIdx.SRC_ROW]))
            retval.append(
                "\tDST: " + " ".join(f"{ROWS_INDEXED[row]}{idx:03}" for row, idx in zip(cons[ConnIdx.DST_ROW], cons[ConnIdx.DST_IDX]))
            )
            retval.append("")
        return "\n".join(retval)

    def __eq__(self, __value: object) -> bool:
        """Return True if the connections are equal to the value."""
        if not isinstance(__value, connections):
            return super().__eq__(__value)
        return array_equal(self, __value)

    def __hash__(self):
        """Generate a hash for the connections object."""
        return hash(self.data)

    def get_connections(self, row: Row, cls: EndPointClassStr) -> ndarray:
        """Return the connections where one end matches row and key[1] class (s or d)."""
        sord: ConnIdx = ConnIdx.SRC_ROW if cls == "s" else ConnIdx.DST_ROW
        row_index: SrcRowIndex | DstRowIndex = SOURCE_ROW_INDEXES[row] if cls == "s" else DESTINATION_ROW_INDEXES[row]  # type: ignore
        return self[:, self[sord] == row_index]

    def get_src_connections(self, sri: SrcRowIndex) -> ndarray:
        """Return the connections where the source row matches row."""
        return self[:, self[ConnIdx.SRC_ROW] == sri]

    def get_dst_connections(self, dri: DstRowIndex) -> ndarray:
        """Return the connections where the destination row matches row."""
        return self[:, self[ConnIdx.DST_ROW] == dri]

    def mermaid(self) -> list[str]:
        """Return the mermaid charts string for the connections."""
        return [f"uid{ROWS_INDEXED[sr]}{si:03}s --> uid{ROWS_INDEXED[dr]}{di:03}d" for sr, dr, si, di in self.T]

    @classmethod
    def _random(cls, _rows: rows) -> list[list[int]]:
        """Create a random set of connections."""
        cons: list[list[int]] = [[], [], [], []]
        has_f: bool = _rows.valid(DstRowIndex.F)
        for row in VALID_DESTINATIONS[has_f]:
            dri: DstRowIndex = DESTINATION_ROW_INDEXES[row]
            # Empty rows will be skipped
            for idx, ept in enumerate(_rows[dri]):
                # Find valid source rows with the ept in it
                sri: SrcRowIndex = choice(
                    [SOURCE_ROW_INDEXES[r] for r in VALID_ROW_SOURCES[has_f][row] if ept in _rows[SOURCE_ROW_INDEXES[r]]]
                )
                # The source row is randomly chosen from the valid sources for the destination row
                cons[ConnIdx.SRC_ROW].append(sri)
                # The destination row is known
                cons[ConnIdx.DST_ROW].append(dri)
                # Randomly choose an endpoint of the selected type in the source row
                cons[ConnIdx.SRC_IDX].append(choice(where(_rows[sri] == ept)[0]))
                # Destination endpoint index is known
                cons[ConnIdx.DST_IDX].append(idx)
        # Can now figure out row U interface & connections
        # This is most convenient to do with an temporary NDArray
        tcons: NDArray = array(cons)
        row_u_types: list[int] = []
        for sri in SrcRowIndex:
            # Find the unconnected set of source row endpoint indices (as a list to preserve order)
            usri: list[int] = sorted(set(range(len(_rows[sri]))) - set(tcons[ConnIdx.SRC_IDX][where(tcons[ConnIdx.SRC_ROW] == sri)]))
            cons[ConnIdx.SRC_ROW].extend([sri] * len(usri))
            cons[ConnIdx.SRC_IDX].extend(usri)
            cons[ConnIdx.DST_ROW].extend([DstRowIndex.U] * len(usri))
            cons[ConnIdx.DST_IDX].extend(range(len(row_u_types), len(row_u_types) + len(usri)))
            row_u_types.extend(_rows[sri][usri])
        # Define row U interface
        if row_u_types:
            _rows.setu(row_u_types)
        return cons

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
                assert (
                    idx == dst_idx
                ), f"Destination row {ROWS_INDEXED[dst_row_index]} has non-sequential destination endpoint indices:\n{dst_row_indices}"
