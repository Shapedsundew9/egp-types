"""Application layer GC type definitions.

xGCs come in two flavours:
    Application Layer GC's - self contained data using basic python types (this module)
    Gene Pool Cache Layer GC's - linked to genetic_code type objects in the cache but is not in the cache itself (gpc_gcs.py)
"""
from __future__ import annotations
from typing import Any, Self
from copy import deepcopy
from .gc_type_tools import NULL_SIGNATURE_BYTES, signature
from .egp_typing import JSONGraph
from .graph import graph
from .interface import interface
from .connections import connections


class eGC:
    """Embryonic genetic code class (Application Layer).

    Defines the minimal set of fields required to add a genetic code to the genetic code cache using
    self contained data i.e. no links to genetic_code type objects in the cache & types are vanilla python types.
    Too add to the cache genetic code dependencies (signature fields) must already be in the cache.

    Uses strict typing (rather than kwargs) to ensure the genetic code is complete.
    """

    def __init__(  # pylint: disable=dangerous-default-value
        self,
        ancestor_a: bytes | None = None,
        ancestor_b: bytes | None = None,
        gca: bytes | None = None,
        gcb: bytes | None = None,
        json_graph: JSONGraph = {},
        meta_data: dict[str, Any] = {},
        **kwargs,  # Optional fields
    ) -> None:
        """Initialise the genetic code with required fields."""
        self.ancestor_a: bytes = ancestor_a if ancestor_a is not None else NULL_SIGNATURE_BYTES
        self.ancestor_b: bytes = ancestor_b if ancestor_b is not None else NULL_SIGNATURE_BYTES
        self.gca: bytes = gca if gca is not None else NULL_SIGNATURE_BYTES
        self.gcb: bytes = gcb if gcb is not None else NULL_SIGNATURE_BYTES
        self.graph: JSONGraph = json_graph if json_graph else {}
        self.meta_data: dict[str, Any] = meta_data if meta_data else {}
        self.optional: dict[str, Any] = kwargs

    def _io_data(self) -> tuple[interface, interface]:
        """Return the genetic code input / output interface"""
        return graph(self.graph).get_io()

    def clone(self) -> Self:
        """Clone the genetic code."""
        return deepcopy(self)

    def inputs(self) -> bytes:
        """Return the genetic code inputs."""
        return self._io_data()[0].tobytes()

    def outputs(self) -> bytes:
        """Return the genetic code outputs."""
        return self._io_data()[1].tobytes()

    def signature(self) -> bytes:
        """Return the genetic code signature."""
        io_data: tuple[interface, interface] = self._io_data()
        return signature(
            memoryview(self.gca), memoryview(self.gcb), io_data[0].data, io_data[1].data, connections(self.graph).data, self.meta_data
        ).tobytes()


class lGC(eGC):
    """Library genetic code class (Application Layer)."""
