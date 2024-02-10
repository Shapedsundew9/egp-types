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

from itertools import count
from typing import TYPE_CHECKING, Any
from logging import DEBUG, Logger, NullHandler, getLogger

from numpy import array
from numpy.typing import NDArray

from .gc_type_tools import signature


# Type checking
if TYPE_CHECKING:
    from egp_stores.gene_pool_cache import gene_pool_cache


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Constants
FIRST_ACCESS_NUMBER: int = -(2**63)
EMPTY_GC_IDX = 0
PURGED_GC_IDX = 1
GC_FIELDS: tuple[str, ...] = ("gca", "gcb", "ancestor_a", "ancestor_b")


class _genetic_code():
    """A genetic code is a codon with a source interface and a destination interface."""

    gene_pool_cache: gene_pool_cache
    access_number: count = count(FIRST_ACCESS_NUMBER)
    __slots__: list[str] = ["idx"]

    def __init__(self) -> None:
        self.idx: int

    def __getitem__(self, member: str) -> Any:
        """Return the specified member."""
        _genetic_code.gene_pool_cache.access_sequence[self.idx] = next(_genetic_code.access_number)
        return getattr(_genetic_code.gene_pool_cache, member)[self.idx]

    def __setitem__(self, member: str, value: object) -> None:
        """Set the specified member to the specified value."""
        getattr(_genetic_code.gene_pool_cache, member)[self.idx] = value

    def touch(self) -> None:
        """Update the access sequence for the genetic code."""
        self["access_sequence"] = next(_genetic_code.access_number)

    @classmethod
    def reset(cls) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        _genetic_code.gene_pool_cache.reset()
        _genetic_code.access_number = count(FIRST_ACCESS_NUMBER)

    def make_leaf(self, purged_gcs: set[int]) -> list[int]:
        """Turn the GC into a leaf node if aany of its GC dependencies are to be purged.
        A leaf node has all its values derived from dependent GCs stored freeing the dependent
        GCs to be pushed to the GL or deleted. If only a subset of the dependent GCs are to be
        purged then the other may become orphaned i.e. they are no longer needed by this GC and
        if no other GCs need them they can be pushed to the GL or deleted.
        NOTE: Orphans do not HAVE to be purged/deleted. They were not purged for a reason in
        the first place. They may be needed in the future and so are returned to the caller.
        """
        # Determine if anything has been purged
        purged: dict[str, bool] = {m: self[m].idx in purged_gcs for m in GC_FIELDS}

        # Return if nothing has been purged there is nothing to do an no orphans
        if not any(purged.values()):
            return []

        # Calculate fields if anything has been purged
        self["signature"] = self.signature()
        self["genetation"] = self.generation()

        # Which was purged and which is an orphan.
        return [self[m].idx for m in ("gca", "gcb", "ancestor_a", "ancestor_b") if purged[m]]

    def signature(self) -> bytes:
        """Return a globally unique reference for the genetic code."""
        # TODO: This is just a placeholder
        return signature(self["gca"]["signature"], self["gcb"]["signature"], self["graph"].json_graph())

    def generation(self) -> int:
        """Return the generation of the genetic code."""
        return max(self["gca"]["generation"], self["gcb"]["generation"]) + 1

    @classmethod
    def cls_assertions(cls) -> None:
        """Validate assertions for the _genetic_code."""


# Constants
EMPTY_TUPLE = tuple()
EMPTY_GENETIC_CODE = _genetic_code()
PURGED_GENETIC_CODE = _genetic_code()
NO_DESCENDANTS: NDArray = array([], dtype=object)
