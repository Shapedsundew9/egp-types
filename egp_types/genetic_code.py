"""
# Genetic Code Graphs

## Architecture

Genetic codes (GCs) are defined by a directed graph of genetic codes called a genomic library. A terminal node 
genetic code is called a codon. The recursive definition of a genetic code allows it to be most efficiently
stored as a sub-graph within a graph allowing the same GC definition to be connected within other sub-graphs.
The GC graph wrapper defining the sub-graph connectivity is called an interface.

## Implementation

The genomic library can become very large but not all of it is needed at runtime. The interface nodes are implemented 
with lazy loading and pruning to cater for finite storage.
  
# Node abstract base class

The node_base class is an abstract base class that defines the interface
for all nodes in a genomic library.

# Endpoints

An endpoint is a type aliases of the numpy int16 type
Endpoints are used to define connections between interfaces.

# Interfaces

An interface is defined by the interface class which is derived from the node_base class.
An interface has a list of endpoints with 0 to 256 elements.
Endpoints in the interface may be connected as source or destination endpoints.
There are two specialisations of the interface class: source_interface and destination_interface.

# Source Interfaces

A source interface is defined by the source_interface class which is derived from the interface class.
Source interfaces can only have connections to destination interfaces.

# Destination Interfaces

A destination interface is defined by the destination_interface class which is derived from the interface class.
Destination interfaces can only have connections from source interfaces.

# Connections

A connection is defined by the connection class. A connection is a directed edge between a source
interface and a destination interface. A connection has a source endpoint and a destination endpoint
defined by the index of the endpoint in the interface endpoint list.

# Constants

Constants are defined by the constant class which is derived from the source_interface class.
A constant has a string member that defines its value as executable code.
A constant only has one endpoint.

# Codons

Codons are terminal (leaf) nodes defined by the codon class derived from the interface class.

# The Conditional Codon

The conditional codon is a specialisation of the codon class. There is only 1 conditional codon
in the genomic library. It has 1 destination endpoint of egp_type 1 (bool).

# Genetic Codes

A genetic code is defined by the genetic_code class derived from the codon class.
"""

from __future__ import annotations

from gc import collect
from itertools import count
from logging import DEBUG, Logger, NullHandler, getLogger
from typing import Any, Generator, SupportsIndex, cast, Self

from egp_stores.genomic_library import genomic_library
from numpy import argsort, empty, int64, intp, array, uint8, ndarray
from numpy.typing import NDArray
from enum import IntEnum


from .egp_typing import (
    CPI,
    CVI,
    DESTINATION_ROWS,
    SOURCE_ROWS,
    DESTINATION_ROW_INDEXES,
    SOURCE_ROW_INDEXES,
    SrcRowIndex,
    DstRowIndex,
    ConstantExecStr,
    EndPointType,
    JSONGraph,
    EndPointIndex,
    SourceRow
)
from .ep_type import ep_type_lookup
from .interface import EMPTY_INTERFACE, dst_interface, interface, src_interface


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


DEFAULT_STORE_SIZE: int = 2**16
FIRST_ACCESS_NUMBER: int = -(2**63)


class node_base:
    """Base class for all nodes in the genomic library."""

    num_nodes: int = 0

    def __init__(self) -> None:
        """Minimal memory footprint for an empty node."""

    def __new__(cls, *_, **__):
        """Track the number of nodes created."""
        return super().__new__(cls)

    def __del__(self) -> None:
        """Track the number of nodes deleted."""

    def reference(self) -> bytes:
        """Return a globally unique reference for the node."""
        raise NotImplementedError

    @classmethod
    def cls_assertions(cls) -> None:
        """Validate assertions for the node."""

    def assertions(self) -> None:
        """Validate assertions for the node."""
        if len(self.reference()) != 32:
            raise ValueError("reference is not 32 bytes")

    def get_num_nodes(self) -> int:
        """Return the number of nodes in the genomic library."""
        return node_base.num_nodes


class row_c(src_interface):
    """A constant is a source interface with a string member that defines its value as executable code."""

    __slots__: list[str] = ["value"]

    def __init__(self, constants: list[list[ConstantExecStr | EndPointType]]) -> None:
        """Construct a constants row from a list of values and a list of egp_types."""
        self.value: list[str] = [cast(ConstantExecStr, ep[CVI.VAL]) for ep in constants]

    def __new__(cls, constants: list[list[ConstantExecStr | EndPointType]]) -> row_c:
        """Construct a constants row from a list of values and a list of egp_types."""
        return super().__new__(cls, tuple(cast(EndPointType, ep[CVI.TYP]) for ep in constants))


class row_f(dst_interface):
    """Row F is a specialization of the dst_interface."""

    def __init__(self) -> None:
        """No initialization required."""

    def __new__(cls) -> row_f:
        """Construct a row F."""
        return super().__new__(cls, [ep_type_lookup["n2v"]["bool"]])


class store:
    """A memory efficient store for numeric data.

    Data is stored in public members as arrays and indexed.
    It is the responsibility of the calling class to use the right index.
    The class provides a method for returning the next free index
    and marking an index as free.
    When the store is full, the purge method is called to purge unused data.
    The purge method calls the supplied user defined purge function to return
    a list of indices to be purged.
    """

    # The global genomic library
    # Is used in nodes for lazy loading of dependent nodes
    gl: genomic_library = genomic_library()

    def __init__(self, size: int = DEFAULT_STORE_SIZE) -> None:
        """Initialize the store."""
        self.empty_indices: list[int] = [0]
        self.size: int = size
        self._remaining: bool = True
        self.objects: NDArray[Any] = empty(self.size, dtype=object)
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)

    def __getitem__(self, idx: int) -> genetic_code:
        """Return the object at the specified index."""
        return cast(genetic_code, self.objects[idx])

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        if self._remaining:
            return self.empty_indices[0]
        return self.size - len(self.empty_indices)

    def reset(self, size: int = DEFAULT_STORE_SIZE) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self.empty_indices: list[int] = [0]
        self.size: int = size
        self._remaining: bool = True

        # Stored data
        # 8 bytes per element
        self.objects: NDArray[Any] = empty(self.size, dtype=object)
        # 8 bytes per element
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)
        # Total bytes = 16 * size

    def _purge(self) -> list[int]:
        """Purge the store of unused data."""
        # Simply marking the data as unused is insufficient because the purged
        # data may be referenced by other objects. The purge function ensures that
        # all references to the purged data in the store are removed.
        assert not self.empty_indices, "empty_indices is not empty"
        num_to_purge: int = self.size // 4
        _logger.info(f"Purging 25% ({num_to_purge} of {self.size}) of the store")
        purged: NDArray[intp] = argsort(self.access_sequence)[:num_to_purge]
        doomed_objects: set[Any] = {self.objects[int(idx)] for idx in purged}

        # Push doomed objects to the global genomic library if they have value
        # TODO

        # Remove any references to the purged objects
        for idx, obj in enumerate(self.objects):
            cast(_genetic_code, obj).purge(doomed_objects)
            if obj in doomed_objects:
                self.objects[idx] = PURGED_GENETIC_CODE

        # Clean up the heap
        _logger.debug(f"{collect()} unreachable objects not collected after purge.")
        return purged.tolist()

    def assign_index(self, obj: object) -> int:
        """Return the next index for a new node."""
        # Whilst initially filling the store the first (and only) element
        # of self.empty_indices is the next index. Once the store is full
        # self.empty_indices is a list of indices that are free.
        next_index: int
        if not self._remaining:
            if not self.empty_indices:
                # In the event the store is full the purge method is called.
                self.empty_indices = self._purge()
            next_index = self.empty_indices.pop(0)
        else:
            next_index = self.empty_indices[0]
            self.empty_indices[0] += 1
            self._remaining = self.empty_indices[0] < (self.size - 1)
        # Assign the object to the next index and return the index
        self.objects[next_index] = obj
        return next_index

    def assertions(self) -> None:
        """Validate assertions for the store."""
        assert len(self.objects) == self.size
        assert len(self.access_sequence) == self.size
        assert len(self.empty_indices) <= self.size
        if self._remaining:
            assert self.empty_indices[0] < self.size
            for idx in range(self.empty_indices[0]):
                assert isinstance(self.objects[idx], genetic_code)
                self.objects[idx].assertions()
        else:
            for idx, obj in enumerate(self.objects):
                assert isinstance(obj, genetic_code)
                obj.assertions()


class _genetic_code(node_base):
    """A genetic code is a codon with a source interface and a destination interface."""

    data_store: store = store()
    access_number: count = count(FIRST_ACCESS_NUMBER)
    __slots__: list[str] = ["gca", "gcb", "_src_ifs", "_dst_ifs", "ancestor_a", "ancestor_b", "idx"]

    def __init__(self) -> None:
        self.gca: _genetic_code
        self.gcb: _genetic_code
        self.graph: graph
        self.ancestor_a: _genetic_code
        self.ancestor_b: _genetic_code
        self.decendants: NDArray
        self.idx: int
        super().__init__()

    def touch(self) -> None:
        """Update the access sequence for the genetic code."""
        _genetic_code.data_store.access_sequence[self.idx] = next(_genetic_code.access_number)

    def purge(self, purged_gcs: set[_genetic_code]) -> None:
        """Remove any references to the purged genetic codes."""
        # So that we can tell the difference between a genuinely null genetic code reference
        # and a purged genetic code reference, we set the genetic code reference to the
        # purged genetic code if it is to be purged from the data store (and memory).
        if isinstance(self, genetic_code):
            if self.gca in purged_gcs:
                self.gca = PURGED_GENETIC_CODE
            if self.gcb in purged_gcs:
                self.gcb = PURGED_GENETIC_CODE
            if self.ancestor_a in purged_gcs:
                self.ancestor_a = PURGED_GENETIC_CODE
            if self.ancestor_b in purged_gcs:
                self.ancestor_b = PURGED_GENETIC_CODE

    def reference(self) -> bytes:
        """Return a globally unique reference for the genetic code."""
        # TODO: This is just a placeholder
        return self.idx.to_bytes(32, "big")

    @classmethod
    def cls_assertions(cls) -> None:
        """Validate assertions for the _genetic_code."""
        super().cls_assertions()


# Constants
EMPTY_TUPLE = tuple()
EMPTY_ROW_C = row_c([])
ROW_F = row_f()
EMPTY_GENETIC_CODE = _genetic_code()
PURGED_GENETIC_CODE = _genetic_code()
NO_DESCENDANTS: NDArray = array([], dtype=object)


class genetic_code(_genetic_code):
    """A genetic code is a codon with a source interface and a destination interface."""

    __slots__: list[str] = ["gca", "gcb", "_src_ifs", "_dst_ifs", "ancestor_a", "ancestor_b", "decendants", "idx"]

    def __init__(self, gc_dict: dict[str, Any] = {}) -> None:  # pylint: disable=dangerous-default-value
        self.gca: _genetic_code = gc_dict.get("gca", EMPTY_GENETIC_CODE)
        self.gcb: _genetic_code = gc_dict.get("gcb", EMPTY_GENETIC_CODE)
        self.graph: graph = graph(gc_dict.get("graph", {}), self.gca, self.gcb)
        self.ancestor_a: _genetic_code = gc_dict.get("ancestor_a", EMPTY_GENETIC_CODE)
        self.ancestor_b: _genetic_code = gc_dict.get("ancestor_b", EMPTY_GENETIC_CODE)
        self.decendants: NDArray = array(gc_dict["decendants"], dtype=object) if "descendants" in gc_dict else NO_DESCENDANTS
        self.idx: int = _genetic_code.data_store.assign_index(self)
        self.touch()
        _genetic_code.num_nodes += 1
        super().__init__()

    def __del__(self) -> None:
        """Track the number of genetic codes deleted."""
        _genetic_code.num_nodes -= 1
        super().__del__()

    @classmethod
    def reset(cls, size: int = DEFAULT_STORE_SIZE) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        _genetic_code.data_store.reset(size)
        _genetic_code.access_number = count(FIRST_ACCESS_NUMBER)
        _genetic_code.num_nodes = 0

    @classmethod
    def cls_assertions(cls) -> None:
        """Validate assertions for the genetic code."""
        _genetic_code.data_store.assertions()
        assert len(_genetic_code.data_store) == _genetic_code.num_nodes
        super().cls_assertions()


class ConnIdx(IntEnum):
    """Indices for connection definitions."""
    SRC_ROW = 0
    DST_ROW = 1
    SRC_IDX = 2
    DST_IDX = 3


class connections(ndarray):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        json_graph: JSONGraph = cast(JSONGraph, kwargs["json_graph"])
        self[ConnIdx.SRC_ROW] = [SOURCE_ROW_INDEXES[cast(SourceRow, ep[CPI.ROW])] for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.DST_ROW] = [DESTINATION_ROW_INDEXES[row] for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.SRC_IDX] = [cast(int, ep[CPI.IDX]) for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]
        self[ConnIdx.DST_IDX] = [cast(int, ep[CPI.IDX]) for row in json_graph for ep in json_graph[row] if row in DESTINATION_ROWS]

    def __new__(cls, *_, **kwargs) -> connections:
        """Create a byte array for the connection data """
        shape: tuple[int, int] = (4, sum(len(val) for row, val in kwargs["json_graph"].items() if row in DESTINATION_ROWS))
        return super().__new__(cls, shape, dtype=uint8)  # pylint: disable=unexpected-keyword-arg


class rows(ndarray):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        json_graph: JSONGraph = cast(JSONGraph, kwargs["json_graph"])
        gca: _genetic_code = cast(_genetic_code, kwargs["gca"])
        gcb: _genetic_code = cast(_genetic_code, kwargs["gcb"])
        self[SrcRowIndex.I] = self.i_if_from_graph(json_graph)
        self[SrcRowIndex.C] = self.row_c_from_graph(json_graph)
        self[SrcRowIndex.A] = gca.graph.interface[SrcRowIndex.I] if gca is not EMPTY_GENETIC_CODE else EMPTY_INTERFACE
        self[SrcRowIndex.B] = gcb.graph.interface[SrcRowIndex.I] if gcb is not EMPTY_GENETIC_CODE else EMPTY_INTERFACE
        self[DstRowIndex.F] = ROW_F if "F" in json_graph else EMPTY_INTERFACE
        self[DstRowIndex.A] = gca.graph.interface[DstRowIndex.A] if gca is not EMPTY_GENETIC_CODE else EMPTY_INTERFACE
        self[DstRowIndex.B] = gcb.graph.interface[DstRowIndex.B] if gcb is not EMPTY_GENETIC_CODE else EMPTY_INTERFACE
        self[DstRowIndex.O] = (
            interface(cast(EndPointType, src_ep[CPI.TYP]) for src_ep in json_graph["O"]) if "O" in json_graph and json_graph["O"] else EMPTY_INTERFACE
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

    def row_c_from_graph(self, json_graph: JSONGraph) -> row_c:
        """Return the C source interface for a genetic code application graph."""
        return row_c(cast(list[list[ConstantExecStr | EndPointType]], json_graph["C"])) if "C" in json_graph and json_graph["C"] else EMPTY_ROW_C


class graph():

    def __init__(self, json_graph: JSONGraph, gca: _genetic_code, gcb: _genetic_code) -> None:
        self.interface: NDArray = empty((len(SOURCE_ROWS) + len(DESTINATION_ROWS),), dtype=object)
        self.connection: connections = connections(json_graph=json_graph)


