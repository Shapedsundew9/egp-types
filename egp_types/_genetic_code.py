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
from logging import DEBUG, Logger, NullHandler, getLogger
from typing import TYPE_CHECKING, Any

from numpy import array, zeros, bytes_
from numpy.typing import NDArray

from .gc_type_tools import signature

# Type checking
if TYPE_CHECKING:
    from egp_stores.gene_pool_cache import gene_pool_cache
    from .interface import interface


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
_LOG_DEEP_DEBUG: bool = _logger.isEnabledFor(DEBUG - 1)


# Constants
FIRST_ACCESS_NUMBER: int = 0  # iinfo(int64).min
GC_OBJ_FIELDS: tuple[str, ...] = ("gca", "gcb", "ancestor_a", "ancestor_b", "pgc")
PROXY_SIGNATURE_FIELDS: tuple[str, ...] = tuple(m + "_signature" for m in GC_OBJ_FIELDS)
SIGNATURE_FIELDS: tuple[str, ...] = PROXY_SIGNATURE_FIELDS + ("signature",)
NULL_SIGNATURE: NDArray[bytes_] = zeros(32, dtype=bytes_)
DIRTY_MEMBERS: set[str] = set()


class _genetic_code:
    """A genetic code is a codon with a source interface and a destination interface."""

    gene_pool_cache: gene_pool_cache
    access_number: count = count(FIRST_ACCESS_NUMBER)
    __slots__: list[str] = ["idx"]

    def __init__(self) -> None:
        self.idx: int

    def __getitem__(self, member: str) -> Any:
        """Return the specified member."""
        # Touch
        _genetic_code.gene_pool_cache.access_sequence[self.idx] = next(_genetic_code.access_number)
        if _LOG_DEEP_DEBUG:
            _logger.debug(
                f"Read access of '{member}' of genetic code {self.idx} sequence number "
                f"{_genetic_code.gene_pool_cache.access_sequence[self.idx]}."
            )
        return _genetic_code.gene_pool_cache[member][self.idx]

    def __repr__(self) -> str:
        """Return the string representation of the genetic code."""
        str_list: list[str] = [f"Genetic Code {self.idx}"]
        str_list.extend([f"  {m}: {type(self[m])}: {self[m]}" for m in SIGNATURE_FIELDS])
        str_list.extend([f"  {m}: {type(self[m])}: <---NOT DISPLAYED-->" for m in GC_OBJ_FIELDS])
        return "\n".join(str_list)

    def __setitem__(self, member: str, value: object) -> None:
        """Set the specified member to the specified value."""
        # Touch
        _genetic_code.gene_pool_cache.access_sequence[self.idx] = next(_genetic_code.access_number)
        if member in DIRTY_MEMBERS:
            # Mark as dirty (push to GP on eviction) if the member updated is one that needs to be preserved.
            _genetic_code.gene_pool_cache.status_byte[self.idx] |= 1
        if _LOG_DEEP_DEBUG:
            _logger.debug(
                f"Write access of '{member}' of genetic code {self.idx} sequence number "
                f"{_genetic_code.gene_pool_cache.access_sequence[self.idx]}."
            )
        _genetic_code.gene_pool_cache[member][self.idx] = value

    def touch(self) -> None:
        """Update the access sequence for the genetic code."""
        _genetic_code.gene_pool_cache.access_sequence[self.idx] = next(_genetic_code.access_number)

    def valid(self) -> bool:
        """Return True if the genetic code is not empty or purged."""
        return self.idx >= 0

    @classmethod
    def reset(cls, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        _genetic_code.gene_pool_cache.reset(size)
        _genetic_code.access_number = count(FIRST_ACCESS_NUMBER)

    @classmethod
    def get_gpc(cls) -> gene_pool_cache:
        """Return the gene pool cache."""
        return _genetic_code.gene_pool_cache

    @classmethod
    def set_gpc(cls, gpc: Any) -> None:
        """Set the gene pool cache."""
        _genetic_code.gene_pool_cache = gpc

    def purge(self, purged_gcs: set[int]) -> list[int]:
        """Turn the GC into a leaf node if any of its GC dependencies are to be purged.
        A leaf node has all its values derived from dependent GCs stored freeing the dependent
        GCs to be pushed to the GL or deleted. If only a subset of the dependent GCs are to be
        purged then the other may become orphaned i.e. they are no longer needed by this GC and
        if no other GCs need them they can be pushed to the GL or deleted.
        NOTE: Orphans do not HAVE to be purged/deleted. They were not purged for a reason in
        the first place. They may be needed in the future and so are returned to the caller.
        """
        # Determine if anything has been purged: This is a search so a "no touch" activity.
        purged: dict[str, bool] = {m: getattr(getattr(_genetic_code.gene_pool_cache, m), "idx", -1) in purged_gcs for m in GC_OBJ_FIELDS}

        # Return if nothing has been purged there is nothing to do an no orphans
        if not any(purged.values()):
            return []

        # Make the genetic code a leaf node, mark those purged as purged and return the potential orphans.
        self.make_leaf()
        for member, _ in filter(lambda x: x[1], purged.items()):
            self[member] = PURGED_GENETIC_CODE
        return [self[m].idx for m in GC_OBJ_FIELDS if not purged[m]]

    def init_as_leaf(self, gc_dict: dict[str, Any]) -> None:
        """Initialise the leaf members deriving where possible."""
        for mstr, mobj in filter(lambda x: x[0] in GC_OBJ_FIELDS and isinstance(x[1], memoryview), gc_dict.items()):
            self[mstr + "_signature"] = mobj
            self[mstr] = PURGED_GENETIC_CODE
        if self["gca"] is not PURGED_GENETIC_CODE and self["gcb"] is not PURGED_GENETIC_CODE:
            self.make_leaf()
        else:
            # If either one of GCA or GCB is purged then the derived values have to be in gc_dict.
            self["code_depth"] = gc_dict["code_depth"]
            self["codon_depth"] = gc_dict["codon_depth"]
            self["generation"] = gc_dict["generation"]
            self["num_codes"] = gc_dict["num_codes"]
            self["num_codons"] = gc_dict["num_codons"]
        self["signature"] = self.signature()

    def make_leaf(self) -> None:
        """Make the genetic code a leaf node by calculating the fields that are derived from other
        genetic codes and stored. This allows the other genetic codes to be purged or deleted."""
        if _LOG_DEEP_DEBUG:
            _logger.debug(f"Making genetic code {self.idx} a leaf node:\n{self}")
        for member in filter(lambda x: self[x] is not PURGED_GENETIC_CODE, GC_OBJ_FIELDS):
            self[member + "_signature"] = self[member]["signature"]
        self["code_depth"] = self.code_depth()
        self["codon_depth"] = self.codon_depth()
        self["generation"] = self.generation()
        self["num_codes"] = self.num_codes()
        self["num_codons"] = self.num_codons()
        self["signature"] = self.signature()

    def signature(self) -> NDArray:
        """Return a globally unique reference for the genetic code."""
        # NOTE: Since a codon is always a leaf it always has its signature defined in the
        # dynamic store when loaded. Therefore the inline part of the signature definition
        # is never needed.
        io_data: tuple[interface, interface] = self["graph"].get_io()
        return signature(
            self["gca"]["signature"].data,
            self["gcb"]["signature"].data,
            io_data[0].data,
            io_data[1].data,
            self["graph"].connections.data
        )

    def code_depth(self) -> int:
        """Return the depth of the genetic code."""
        return max(self["gca"]["code_depth"], self["gcb"]["code_depth"]) + 1

    def codon_depth(self) -> int:
        """Return the depth of the genetic code."""
        return max(self["gca"]["codon_depth"], self["gcb"]["codon_depth"]) + 1

    def generation(self) -> int:
        """Return the generation of the genetic code."""
        return max(self["gca"]["generation"], self["gcb"]["generation"]) + 1

    def num_codes(self) -> int:
        """Return the number of genetic sub-codes that make up this genetic code."""
        return self["gca"]["num_codes"] + self["gcb"]["num_codes"] + 1

    def num_codons(self) -> int:
        """Return the number of codons that make up this genetic code."""
        return self["gca"]["num_codons"] + self["gcb"]["num_codons"] + 1

    @classmethod
    def cls_assertions(cls) -> None:
        """Validate assertions for the _genetic_code."""


class _special_genetic_code(_genetic_code):
    """A special genetic code is simply a stub that returns a constant value for all its members."""

    def __init__(self) -> None:
        self.idx: int = -1

    def __getitem__(self, member: str) -> Any:
        """Return the specified member. Always the default value for a special genetic code."""
        # _logger.debug(f"Read access of '{member}:{DEFAULT_MEMBERS.get(member, 0)}' of special genetic code.")
        return DEFAULT_MEMBERS.get(member, 0)

    def __setitem__(self, member: str, value: object) -> None:
        """Set the specified member to the specified value. Always raises an error."""
        raise RuntimeError("Cannot set a member of a special genetic code.")

    def touch(self) -> None:
        """Do nothing. A special genetic code is never touched."""
        pass

    def valid(self) -> bool:
        """Return False. A special genetic code is never valid."""
        return False

    def purge(self, purged_gcs: set[int]) -> list[int]:
        """Return an empty list. A special genetic code is never a leaf."""
        return []
    
    def signature(self) -> NDArray:
        """This method should never be run as getitem should always return NULL_SIGNATURE."""
        raise RuntimeError("Cannot run signature on a special genetic code.")
    
    def generation(self) -> int:
        """This method should never be run as getitem should always return 0."""
        raise RuntimeError("Cannot run generation on a special genetic code.")


# Constants
EMPTY_TUPLE = tuple()
EMPTY_GENETIC_CODE = _special_genetic_code()
PURGED_GENETIC_CODE = _special_genetic_code()
NO_DESCENDANTS: NDArray = array([], dtype=object)
DEFAULT_MEMBERS: dict[str, Any] = {m: NULL_SIGNATURE for m in SIGNATURE_FIELDS}
DEFAULT_MEMBERS.update({m: EMPTY_GENETIC_CODE for m in GC_OBJ_FIELDS})
