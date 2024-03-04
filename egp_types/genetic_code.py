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

from logging import DEBUG, Logger, NullHandler, getLogger
from pprint import pformat
from random import randbytes
from typing import Any
from uuid import UUID
from itertools import count

from ._genetic_code import (
    DEFAULT_DYNAMIC_MEMBER_VALUES,
    STORE_STATIC_NON_OBJECT_MEMBERS,
    DEFAULT_STATIC_MEMBER_VALUES,
    PURGED_GENETIC_CODE,
    EMPTY_GENETIC_CODE,
    STORE_DERIVED_MEMBERS,
    STORE_GC_OBJ_MEMBERS,
    _genetic_code,
)
from .egp_typing import DstRowIndex, SrcRowIndex, JSONGraph
from .graph import EMPTY_GRAPH, graph
from .interface import EMPTY_IO, interface
from .rows import rows

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Circular reference on graph definition in _genetic_code.py
DEFAULT_STATIC_MEMBER_VALUES["graph"] = EMPTY_GRAPH
PREDEFINED_MEMBERS: set[str] = {"gca", "gcb", "graph"}
CODON_CREATOR_UUID = UUID("22c23596-df90-4b87-88a4-9409a0ea764f")


# Uniquely number genetic code classes
gc_class_number = count()


class genetic_code(_genetic_code):
    """A genetic code is a codon with a source interface and a destination interface."""

    def __init__(self, gc_graph: dict[str, Any] = {}, **kwargs) -> None:  # pylint: disable=dangerous-default-value
        # All data is in the class store to keep it compact.
        # The store is a singleton and is shared by all instances of the class.
        # Runtime for genetic_code operations is not critical path but memory is.
        cls = type(self)
        self.idx: int = cls.genetic_code_cache.assign_index(self)
        self.touch()
        super().__init__()
        # Generate a random genetic code if the "rndm" key is in the gc_dict.
        if kwargs.get("rndm", False):
            kwargs.setdefault("depth", 5)
            kwargs.setdefault("io", EMPTY_IO)
            self.random(**kwargs)
        else:
            if _LOG_DEBUG:
                _logger.debug(f"genetic_code {self.idx} creating from:\n{pformat(gc_graph)}")
                if "signature" in gc_graph and isinstance(gc_graph["signature"], memoryview):
                    _logger.debug(f"'signature' {gc_graph['signature'].hex()}")
            # Build a genetic code from the gc_dict
            # First see if it needs to be a leaf node
            codon: bool = "creator" in gc_graph and gc_graph["creator"] == CODON_CREATOR_UUID
            for member in STORE_GC_OBJ_MEMBERS:
                self[member] = self.gcx(gc_graph.get(member))
                if isinstance(gc_graph.get(member), memoryview):
                    self[member + "_signature"] = gc_graph[member]
            io: tuple[interface, interface] = gc_graph.get("io", EMPTY_IO)
            self["graph"] = graph(gc_graph.get("graph", {}), gca=self["gca"], gcb=self["gcb"], io=io)
            for member in STORE_STATIC_NON_OBJECT_MEMBERS:
                self[member] = gc_graph.get(member, DEFAULT_STATIC_MEMBER_VALUES[member])
            if self["gca"] is not PURGED_GENETIC_CODE and self["gcb"] is not PURGED_GENETIC_CODE and not codon:
                for member in STORE_DERIVED_MEMBERS:
                    # This looks weird but it will generate the derived members when __getitem__ is called.
                    self[member] = self[member]
            else:
                # If either one of GCA or GCB is purged then the derived values have to be in gc_dict or default
                # The direct update to the GC derived members will mark them dirty but they are not so
                # the GC dirty bit is cleared.
                for member in STORE_DERIVED_MEMBERS:
                    self[member] = gc_graph.get(member, DEFAULT_DYNAMIC_MEMBER_VALUES[member])
                self.clean()
        if _LOG_DEBUG:
            _logger.debug(f"genetic_code {self.idx} created:\n{self}")

    def get_interface(self, iface: str = "IO") -> tuple[interface, interface]:
        """Return the source and destination interfaces."""
        # Access to rows would be a circular reference in _genetic_code.
        _rows: rows = self["graph"].rows
        if iface == "IO":
            return _rows[SrcRowIndex.I], _rows[DstRowIndex.O]
        if iface == "A":
            return _rows[SrcRowIndex.A], _rows[DstRowIndex.A]
        if iface == "B":
            return _rows[SrcRowIndex.B], _rows[DstRowIndex.B]
        assert False, f"Unknown interface {iface}"

    def random(self, depth: int = 5, io: tuple[interface, interface] = EMPTY_IO, **kwargs) -> None:
        """Create a random genetic code with up to depth levels of sub-graphs."""
        # Access to graph would be a circular reference in _genetic_code.
        cls = type(self)
        assert 2**depth < cls.genetic_code_cache.size(), "Recursive depth too large."
        if depth:
            self["graph"] = graph({}, **kwargs)
            kwargs["depth"] = depth - 1
            kwargs["io"] = self.get_interface("A")
            self["gca"] = cls({}, **kwargs)
            kwargs["io"] = self.get_interface("B")
            self["gcb"] = cls({}, **kwargs)
        else:
            # At the leaf level the graph is a single codon.
            kwargs["rows"] = "IAO"
            self["graph"] = graph({}, **kwargs)
            self["gca"] = EMPTY_GENETIC_CODE
            self["gcb"] = EMPTY_GENETIC_CODE
            self["generation"] = 0
            self["signature"] = randbytes(32)


def genetic_code_factory() -> type[_genetic_code]:
    """Return the next genetic_code class."""
    return type(f"genetic_code_{next(gc_class_number)}", (genetic_code,), {})
