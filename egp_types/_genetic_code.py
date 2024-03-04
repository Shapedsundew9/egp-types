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
from typing import TYPE_CHECKING, Any, Callable

from numpy import array, zeros, bytes_, int32, int64, intp, float32, ndarray, signedinteger, floating
from numpy.typing import NDArray

from .gc_type_tools import signature


# Type checking
if TYPE_CHECKING:
    from .genetic_code_cache import genetic_code_cache
    from .interface import interface


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
_LOG_DEEP_DEBUG: bool = _logger.isEnabledFor(DEBUG - 1)


# Constants
FIRST_ACCESS_NUMBER: int = 0  # iinfo(int64).min
STORE_GC_OBJ_MEMBERS: tuple[str, ...] = ("gca", "gcb", "ancestor_a", "ancestor_b", "pgc")
STORE_PROXY_SIGNATURE_MEMBERS: tuple[str, ...] = tuple(m + "_signature" for m in STORE_GC_OBJ_MEMBERS)
STORE_SIGNATURE_MEMBERS: tuple[str, ...] = STORE_PROXY_SIGNATURE_MEMBERS + ("signature",)
NULL_SIGNATURE: NDArray[bytes_] = zeros(32, dtype=bytes_)
STORE_DEFAULT_MEMBERS: tuple[str, ...] = ("e_count", "evolvability", "f_count", "fitness", "reference_count", "survivability")
STORE_DIRTY_MEMBERS: set[str] = set(STORE_DEFAULT_MEMBERS)
STORE_STATIC_NON_OBJECT_MEMBERS: tuple[str, ...] = (
    "e_count",
    "evolvability",
    "f_count",
    "fitness",
    "properties",
    "reference_count",
    "survivability",
)  # graph is a non-gc object object member
STORE_STATIC_MEMBERS: tuple[str, ...] = STORE_GC_OBJ_MEMBERS + STORE_STATIC_NON_OBJECT_MEMBERS + ("graph",)
STORE_DERIVED_MEMBERS: tuple[str, ...] = ("code_depth", "codon_depth", "generation", "num_codes", "num_codons", "signature")
STORE_DYNAMIC_MEMBERS: tuple[str, ...] = STORE_PROXY_SIGNATURE_MEMBERS + STORE_DERIVED_MEMBERS
HIGHER_LAYER_MEMBERS: tuple[str, ...] = STORE_DERIVED_MEMBERS + STORE_STATIC_MEMBERS
STORE_ALL_MEMBERS: tuple[str, ...] = STORE_DYNAMIC_MEMBERS + STORE_STATIC_MEMBERS
INT32_ZERO = int32(0)
INT32_ONE = int32(1)
INT32_MINUS_ONE = int32(-1)
INT64_ZERO = int64(0)
FLOAT32_ZERO = float32(0.0)
FLOAT32_ONE = float32(1.0)


class _genetic_code:
    """A genetic code is a codon with a source interface and a destination interface."""

    genetic_code_cache: genetic_code_cache
    access_number: count = count(FIRST_ACCESS_NUMBER)
    __slots__: list[str] = ["idx"]

    def __init__(self, _: dict[str, Any] = {}, **__) -> None:
        self.idx: int

    def __getitem__(self, member: str) -> Any:
        """Return the specified member."""
        # Touch
        cls = type(self)
        gcc: genetic_code_cache = cls.genetic_code_cache
        gcc.access_sequence[self.idx] = next(cls.access_number)
        if _LOG_DEEP_DEBUG:
            _logger.debug(f"Read access of '{member}' of genetic code {self.idx} sequence number " f"{gcc.access_sequence[self.idx]}.")
        # Returning a static member.
        if member in STORE_STATIC_MEMBERS:
            return getattr(gcc, member)[self.idx]

        # Returning a dynamic member.
        # If the dynamic member is not stored then it is calculated.
        if _LOG_DEBUG:
            assert member in STORE_DYNAMIC_MEMBERS, f"Member '{member}' is not a dynamic member of genetic code."
        return gcc._common_ds_members[member][self.idx]

    def __repr__(self) -> str:
        """Return the string representation of the genetic code."""
        str_list: list[str] = [f"Genetic Code {self.idx}"]
        for member in STORE_ALL_MEMBERS:
            raw_value: Any = self[member]
            if isinstance(raw_value, _genetic_code):
                value: Any = raw_value["signature"].data.hex()
            elif isinstance(raw_value, ndarray):
                value = raw_value.data.hex()
            else:
                value = raw_value
            str_list.append(f"  {member}: {type(self[member])}: {value}")
        return "\n".join(str_list)

    def __setitem__(self, member: str, value: object) -> None:
        """Set the specified member to the specified value."""
        # Touch
        cls = type(self)
        gpc: genetic_code_cache = cls.genetic_code_cache
        gpc.access_sequence[self.idx] = next(cls.access_number)
        if member in STORE_DIRTY_MEMBERS:
            # Mark as dirty (push to GP on eviction) if the member updated is one that needs to be preserved.
            self.dirty()
        if _LOG_DEEP_DEBUG:
            _logger.debug(f"Setting member '{member}' index {self.idx} sequence number " f"{gpc.access_sequence[self.idx]}.")
            if not isinstance(value, _genetic_code):
                _logger.debug(f"value: {value}")
        # Setting a static member.
        if member in STORE_STATIC_MEMBERS:
            getattr(gpc, member)[self.idx] = value
        else:
            # Setting a dynamic member.
            if _LOG_DEEP_DEBUG:
                _logger.debug(f"Setting dynamic member '{member}' dynamic index {gpc.common_ds_idx[self.idx]}.")
                assert member in STORE_DYNAMIC_MEMBERS, f"Member '{member}' is not a dynamic member of genetic code."
            gpc._common_ds_members[member][self.idx] = value
            _logger.debug(f"Set dynamic member '{gpc._common_ds_members[member][self.idx]}.")


    def as_dict(self) -> dict[str, Any]:
        """Return the genetic code as a dictionary."""
        retval: dict[str, Any] = {}
        for member in HIGHER_LAYER_MEMBERS:
            raw_value: Any = self[member]
            if isinstance(raw_value, _genetic_code):
                if raw_value is EMPTY_GENETIC_CODE:
                    value = None
                elif raw_value is PURGED_GENETIC_CODE:
                    value: Any = self[member + "_signature"].data
                else:
                    value = raw_value["signature"].data
            elif isinstance(raw_value, signedinteger):
                value = int(raw_value)
            elif isinstance(raw_value, floating):
                value = float(raw_value)
            elif member == "signature":
                value = raw_value.data
            elif isinstance(raw_value, ndarray):
                value = raw_value.tolist()
            elif raw_value is None:
                value = None
            elif member == "graph":
                value = raw_value.json_graph()
            else:
                raise RuntimeError(f"Unknown type {type(raw_value)} for member {member}")
            retval[member] = value
        return retval

    def assertions(self) -> None:
        """Validate assertions for the genetic code."""
        self["graph"].assertions()

    def ancestor_a_signature(self) -> NDArray:
        """Return the signature of the genetic code."""
        return self["ancestor_a"]["signature"]

    def ancestor_b_signature(self) -> NDArray:
        """Return the signature of the genetic code."""
        return self["ancestor_b"]["signature"]

    def clean(self) -> None:
        """Set the state of the GC to clean."""
        type(self).genetic_code_cache.status_byte[self.idx] &= 0xFE

    def code_depth(self) -> int32:
        """Return the depth of the genetic code."""
        return max(self["gca"]["code_depth"], self["gcb"]["code_depth"]) + 1

    def codon_depth(self) -> int32:
        """Return the depth of the genetic code."""
        return max(self["gca"]["codon_depth"], self["gcb"]["codon_depth"]) + 1

    def dirty(self) -> None:
        """Set the state of the GC to dirty."""
        type(self).genetic_code_cache.status_byte[self.idx] |= 1

    def gca_signature(self) -> NDArray:
        """Return the signature of the genetic code."""
        return self["gca"]["signature"]

    def gcb_signature(self) -> NDArray:
        """Return the signature of the genetic code."""
        return self["gcb"]["signature"]

    def gcx(self, gcx: Any) -> _genetic_code:
        """Return the appropriate value for GCx based on its type."""
        if isinstance(gcx, _genetic_code):
            return gcx
        if gcx is None:
            return EMPTY_GENETIC_CODE
        if isinstance(gcx, memoryview):
            return PURGED_GENETIC_CODE
        assert False, f"Invalid genetic code type {type(gcx)}"

    def generation(self) -> int64:
        """Return the generation of the genetic code."""
        return max(self["gca"]["generation"], self["gcb"]["generation"]) + 1

    def is_dirty(self) -> bool:
        """Return True if the genetic code is dirty."""
        return bool(type(self).genetic_code_cache.status_byte[self.idx] & 1)

    def make_leaf(self) -> None:
        """Make the genetic code a leaf node by calculating the fields that are derived from other
        genetic codes and stored. This allows the other genetic codes to be purged or deleted."""
        if _LOG_DEEP_DEBUG:
            _logger.debug(f"Making genetic code {self.idx} a leaf node.")
        for member in STORE_GC_OBJ_MEMBERS:
            self[member + "_signature"] = self[member]["signature"]
        for member in STORE_DERIVED_MEMBERS:
            # This looks weird but it will generate the derived members when __getitem__ is called.
            self[member] = self[member]

    def mermaid(self) -> list[str]:
        """Return the Mermaid Chart representation of the genetic code."""
        header: list[str] = ["---", f"title: Genetic Code instance {id(self)}", "---", "flowchart TB"]
        # TODO: Complete this function
        return header

    def num_codes(self) -> int32:
        """Return the number of genetic sub-codes that make up this genetic code."""
        return self["gca"]["num_codes"] + self["gcb"]["num_codes"] + 1

    def num_codons(self) -> int32:
        """Return the number of codons that make up this genetic code."""
        return self["gca"]["num_codons"] + self["gcb"]["num_codons"] + 1

    def pgc_signature(self) -> NDArray:
        """Return the signature of the genetic code."""
        return self["pgc"]["signature"]

    def properties(self) -> int64:
        """Return the properties of the genetic code."""
        # FIXME: Properties are derived from GCA & GCB but may be AND'd, OR'd and may be added too.
        return self["gca"]["properties"] | self["gcb"]["properties"]

    def purge(self, purged_gcs: set[intp]) -> list[intp]:
        """Turn the GC into a leaf node if any of its GC dependencies are to be purged.
        A leaf node has all its values derived from dependent GCs stored freeing the dependent
        GCs to be pushed to the GL or deleted. If only a subset of the dependent GCs are to be
        purged then the other may become orphaned i.e. they are no longer needed by this GC and
        if no other GCs need them they can be pushed to the GL or deleted.
        NOTE: Orphans do not HAVE to be purged/deleted. They were not purged for a reason in
        the first place. They may be needed in the future and so are returned to the caller.
        """
        # Determine if anything has been purged: This is a search so a "no touch" activity.
        cls = type(self)
        purged: dict[str, bool] = {m: getattr(getattr(cls.genetic_code_cache, m), "idx", -1) in purged_gcs for m in STORE_GC_OBJ_MEMBERS}

        # Return if nothing has been purged there is nothing to do an no orphans
        if not any(purged.values()):
            return []

        # Make the genetic code a leaf node, mark those purged as purged and return the potential orphans.
        self.make_leaf()
        for member, _ in filter(lambda x: x[1], purged.items()):
            self[member] = PURGED_GENETIC_CODE
        return [self[m].idx for m in STORE_GC_OBJ_MEMBERS if not purged[m]]

    def signature(self) -> NDArray:
        """Return a globally unique reference for the genetic code."""
        # NOTE: Since a codon is always a leaf it always has its signature defined in the
        # dynamic store when loaded. Therefore the inline part of the signature definition
        # is never needed.
        io_data: tuple[interface, interface] = self["graph"].get_io()
        retval =  signature(
            self["gca"]["signature"].data, self["gcb"]["signature"].data, io_data[0].data, io_data[1].data, self["graph"].connections.data
        )
        _logger.debug(f"Signature of genetic code {self.idx}: {retval.data.hex()}")
        return retval

    def touch(self) -> None:
        """Update the access sequence for the genetic code."""
        cls = type(self)
        cls.genetic_code_cache.access_sequence[self.idx] = next(cls.access_number)

    def valid(self) -> bool:
        """Return True if the genetic code is not empty or purged."""
        return self.idx >= 0

    @classmethod
    def get_gpc(cls) -> genetic_code_cache:
        """Return the gene pool cache."""
        return cls.genetic_code_cache

    @classmethod
    def reset(cls, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        cls.genetic_code_cache.reset(size)
        cls.access_number = count(FIRST_ACCESS_NUMBER)

    @classmethod
    def set_gpc(cls, gpc: Any) -> None:
        """Set the gene pool cache."""
        cls.genetic_code_cache = gpc


class _special_genetic_code(_genetic_code):
    """A special genetic code is simply a stub that returns a constant value for all its members."""

    def __init__(self) -> None:
        """Initialise the special genetic code. Index is always -1."""
        super().__init__()
        self.idx: int = -1

    def __getitem__(self, member: str) -> Any:
        """Return the specified member default value."""
        if member in STORE_STATIC_MEMBERS:
            return DEFAULT_STATIC_MEMBER_VALUES[member]
        return DEFAULT_DYNAMIC_MEMBER_VALUES[member]

    def __setitem__(self, member: str, value: object) -> None:
        """Set the specified member to the specified value. Always raises an error."""
        raise RuntimeError("Cannot set a member of a special genetic code.")

    def code_depth(self) -> int32:
        """Return the depth of the genetic code."""
        return INT32_ZERO

    def codon_depth(self) -> int32:
        """Return the depth of the genetic code."""
        return INT32_ZERO

    def generation(self) -> int64:
        """Return the generation of the genetic code."""
        return INT64_ZERO

    def num_codes(self) -> int32:
        """Return the number of genetic sub-codes that make up this genetic code."""
        return INT32_ZERO

    def num_codons(self) -> int32:
        """Return the number of codons that make up this genetic code."""
        return INT32_ZERO

    def purge(self, _: set[int]) -> list[int]:
        """Return an empty list. A special genetic code is never a leaf."""
        return []

    def properties(self) -> int64:
        return DEFAULT_PROPERTIES

    def signature(self) -> NDArray:
        """Return the null signature."""
        return NULL_SIGNATURE

    def touch(self) -> None:
        """Do nothing. A special genetic code is never touched."""

    def valid(self) -> bool:
        """Return False. A special genetic code is never valid."""
        return False


# Constants
EMPTY_TUPLE = tuple()
EMPTY_GENETIC_CODE = _special_genetic_code()
PURGED_GENETIC_CODE = _special_genetic_code()
NO_DESCENDANTS: NDArray = array([], dtype=object)
DEFAULT_MEMBERS: dict[str, Any] = {m: NULL_SIGNATURE for m in STORE_SIGNATURE_MEMBERS}
DEFAULT_MEMBERS.update({m: EMPTY_GENETIC_CODE for m in STORE_GC_OBJ_MEMBERS})
DEFAULT_PROPERTIES: int64 = INT64_ZERO
DEFAULT_STATIC_MEMBER_VALUES: dict[str, Any] = {
    "_e_count": INT32_ONE,
    "_evolvability": FLOAT32_ONE,
    "_reference_count": INT64_ZERO,
    "ancestor_a": EMPTY_GENETIC_CODE,
    "ancestor_b": EMPTY_GENETIC_CODE,
    "e_count": INT32_ONE,
    "evolvability": FLOAT32_ONE,
    "f_count": INT32_ZERO,
    "fitness": FLOAT32_ZERO,
    "gca": EMPTY_GENETIC_CODE,
    "gcb": EMPTY_GENETIC_CODE,
    "graph": None,  # Circular reference issue: Updated to EMPTY_GRAPH in genetic_code.py
    "pgc": EMPTY_GENETIC_CODE,
    "properties": DEFAULT_PROPERTIES,
    "reference_count": INT64_ZERO,
    "survivability": FLOAT32_ZERO,
}
DEFAULT_DYNAMIC_MEMBER_VALUES: dict[str, Any] = {
    "code_depth": INT32_ZERO,
    "codon_depth": INT32_ZERO,
    "generation": INT64_ZERO,
    "num_codes": INT32_ONE,
    "num_codons": INT32_ONE,
    "signature": NULL_SIGNATURE,
}
DEFAULT_DYNAMIC_MEMBER_VALUES.update({m: NULL_SIGNATURE for m in STORE_PROXY_SIGNATURE_MEMBERS})
is_valid_gc: Callable[..., bool] = lambda x: x is not PURGED_GENETIC_CODE and x is not EMPTY_GENETIC_CODE
