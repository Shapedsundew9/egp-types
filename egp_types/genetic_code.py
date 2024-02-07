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

from typing import Any
from logging import DEBUG, Logger, NullHandler, getLogger

from numpy import array

from ._genetic_code import _genetic_code, EMPTY_GENETIC_CODE, NO_DESCENDANTS
from .egp_typing import DstRowIndex, SrcRowIndex
from .graph import graph
from .rows import rows
from .interface import interface, EMPTY_IO


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class genetic_code(_genetic_code):
    """A genetic code is a codon with a source interface and a destination interface."""

    def __init__(self, gc_dict: dict[str, Any] = {}) -> None:  # pylint: disable=dangerous-default-value
        # All data is in the class store to keep it compact.
        # The store is a singleton and is shared by all instances of the class.
        # Runtime for genetic_code operations is not critical path but memory is.
        self.idx: int = _genetic_code.gene_pool_cache.assign_index(self)
        io: tuple[interface, interface] = gc_dict.get("io", EMPTY_IO)
        self["ancestor_a"] = gc_dict.get("ancestor_a", EMPTY_GENETIC_CODE)
        self["ancestor_b"] = gc_dict.get("ancestor_b", EMPTY_GENETIC_CODE)
        self["descendants"] = array(gc_dict["decendants"], dtype=object) if "descendants" in gc_dict else NO_DESCENDANTS
        self["state"] = gc_dict.get("state", 0)
        self.touch()
        _genetic_code.num_nodes += 1
        super().__init__()
        # Generate a random genetic code if the "rndm" key is in the gc_dict.
        if "rndm" in gc_dict:
            self.random(gc_dict["rndm"])
        else:
            self["gca"] = gc_dict.get("gca", EMPTY_GENETIC_CODE)
            self["gcb"] = gc_dict.get("gcb", EMPTY_GENETIC_CODE)
            self["graph"] = graph(gc_dict.get("graph", {}), gca=self["gca"], gcb=self["gcb"], io=io)

    def __del__(self) -> None:
        """Track the number of genetic codes deleted."""
        _genetic_code.num_nodes -= 1

    @classmethod
    def cls_assertions(cls) -> None:
        """Validate assertions for the genetic code."""
        _genetic_code.gene_pool_cache.assertions()
        assert len(_genetic_code.gene_pool_cache) == _genetic_code.num_nodes
        super().cls_assertions()

    def mermaid(self) -> list[str]:
        """Return the Mermaid Chart representation of the genetic code."""
        header: list[str] = [
            "---",
            f"title: Genetic Code instance {id(self)}",
            "---",
            "flowchart TB"  
        ]
        # TODO: Complete this function
        return header

    def get_interface(self, iface: str = "IO") -> tuple[interface, interface]:
        """Return the source and destination interfaces."""
        _rows: rows = self["graph"].rows
        if iface == "IO":
            return _rows[SrcRowIndex.I], _rows[DstRowIndex.O]
        if iface == "A":
            return _rows[SrcRowIndex.A], _rows[DstRowIndex.A]
        if iface == "B":
            return _rows[SrcRowIndex.B], _rows[DstRowIndex.B]
        assert False, f"Unknown interface {iface}"

    def random(self, depth: int = 5, io: tuple[interface, interface] = EMPTY_IO) -> None:
        """Create a random genetic code with up to depth levels of sub-graphs."""
        self["graph"] = graph({}, rndm=True, io=io)
        if depth:
            self["gca"] = genetic_code({"rndm": depth-1, "io": self.get_interface("A")})
            self["gcb"] = genetic_code({"rndm": depth-1, "io": self.get_interface("B")})

    def assertions(self) -> None:
        """Validate assertions for the genetic code."""
        self["graph"].assertions()
