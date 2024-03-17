"""Basic GP dict GC type definitions.

xGCs come in two flavours:
    Application Layer GC's - self contained data using basic python types.
    Gene Pool Cache Layer GC's - linked to genetic_code type objects in the cache but is not in the cache itself.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any
from copy import deepcopy
from numpy._typing import _8Bit
from numpy.typing import NDArray
from numpy import dtype, uint8, int32, int64, float32, array

from egp_types._genetic_code import _genetic_code
from .gc_type_tools import NULL_SIGNATURE_ARRAY, NULL_SIGNATURE_BYTES, signature, INT32_ONE, INT64_ZERO, FLOAT32_ZERO, FLOAT32_ONE, INT32_ZERO, app_sig_to_array
from .egp_typing import JSONGraph
from .graph import graph
from .interface import interface
from .connections import connections

if TYPE_CHECKING:
    from ._genetic_code import _genetic_code
    from .genetic_code_cache import genetic_code_cache


class _GC:
    """Genetic Code base class."""

    def clone(self) -> _GC:
        """Clone the genetic code."""
        return deepcopy(self)


class eGC(_GC):
    """Embryonic genetic code class (Application Layer).
    
    Defines the minimal set of fields required to add a genetic code to the genetic code cache using
    self contained data i.e. no links to genetic_code type objects in the cache & types are vanilla python types.
    Too add to the cache genetic code dependencies (signature fields) must already be in the cache.

    Uses strict typing (rather than kwargs) to ensure the genetic code is complete.
    """

    def __init__(self,
        ancestor_a: bytes | None = None,
        ancestor_b: bytes | None = None,
        gca: bytes | None = None,
        gcb: bytes | None = None,
        json_graph: JSONGraph = {},
        meta_data: dict[str, Any] = {},
    ) -> None:
        """Initialise the genetic code with required fields."""
        self.ancestor_a: bytes = ancestor_a if ancestor_a is not None else NULL_SIGNATURE_BYTES
        self.ancestor_b: bytes = ancestor_b if ancestor_b is not None else NULL_SIGNATURE_BYTES
        self.gca: bytes = gca if gca is not None else NULL_SIGNATURE_BYTES
        self.gcb: bytes = gcb if gcb is not None else NULL_SIGNATURE_BYTES
        self.graph: JSONGraph = json_graph if json_graph else {}
        self.meta_data: dict[str, Any] = meta_data if meta_data else {}

    def _io_data(self) -> tuple[interface, interface]:
        """Return the genetic code input / output interface"""
        return graph(self.graph).get_io()
    
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
            memoryview(self.gca),
            memoryview(self.gcb),
            io_data[0].data,
            io_data[1].data,
            connections(self.graph).data,
            self.meta_data
        ).tobytes()


class dGC:
    """Default genetic code class (Gene Pool Cache Layer).

    Defines the minimal set of fields required to add a genetic code to the genetic code cache.
    It has the same information as a eGC but all the dependencies are linked to genetic_code type objects and
    types are the same as in the Gene Pool Cache.

    Uses strict typing (rather than kwargs) to ensure the genetic code is complete.    
    """

    def __init__(self, gcc: genetic_code_cache, xGC: eGC | dGC | _genetic_code | None = None) -> None:
        """Initialise the genetic code."""
        self.gcc: genetic_code_cache = gcc
        # All of these must be defined as a static member in _genetic_code.py
        self._e_count: int32 = INT32_ONE
        self._evolvability: float32 = FLOAT32_ONE
        self._reference_count: int64 = INT64_ZERO
        self.ancestor_a: _genetic_code = gcc.EMPTY_GENETIC_CODE
        self.ancestor_b: _genetic_code = gcc.EMPTY_GENETIC_CODE
        self.e_count: int32 = INT32_ONE
        self.evolvability: float32 = FLOAT32_ONE
        self.f_count: int32 = INT32_ZERO
        self.fitness: float32 = FLOAT32_ZERO
        self.gca: _genetic_code = gcc.EMPTY_GENETIC_CODE
        self.gcb: _genetic_code = gcc.EMPTY_GENETIC_CODE
        self.graph: graph = gcc.EMPTY_GRAPH
        self.pgc: _genetic_code = gcc.EMPTY_GENETIC_CODE
        self.properties: int64 = INT64_ZERO
        self.reference_count: int64 = INT64_ZERO
        self.survivability: float32 = FLOAT32_ZERO        
        if isinstance(xGC, dGC):
            self.from_dGC(xGC)
        elif isinstance(xGC, eGC):
            self.from_eGC(xGC)
        elif isinstance(xGC, _genetic_code):
            self.from_GC(xGC)
        
    def from_dGC(self, dGC_: dGC) -> None:
        """Initialise the genetic code from a dGC."""
        self._e_count = dGC_._e_count
        self._evolvability = dGC_._evolvability
        self._reference_count = dGC_._reference_count
        self.ancestor_a = dGC_.ancestor_a
        self.ancestor_b = dGC_.ancestor_b
        self.e_count = dGC_.e_count
        self.evolvability = dGC_.evolvability
        self.f_count = dGC_.f_count
        self.fitness = dGC_.fitness
        self.gca = dGC_.gca
        self.gcb = dGC_.gcb
        self.graph = dGC_.graph
        self.pgc = dGC_.pgc
        self.reference_count = dGC_.reference_count
        self.survivability = dGC_.survivability

    def from_eGC(self, eGC_: eGC) -> None:
        """Initialise the genetic code from a eGC."""
        byte_sigs: tuple[NDArray[uint8], ...] = (
            app_sig_to_array(eGC_.ancestor_a),
            app_sig_to_array(eGC_.ancestor_b),
            app_sig_to_array(eGC_.gca),
            app_sig_to_array(eGC_.gcb)
        )
        gcs: list[_genetic_code] = self.gcc.find(byte_sigs)
        self.ancestor_a = gcs[0]
        self.ancestor_b = gcs[1]
        self.gca = gcs[2]
        self.gcb = gcs[3]
        self.graph = graph(eGC_.graph)
        # dGC does not store meta_data because it has no use in the cache.

    def from_GC(self, GC_: _genetic_code) -> None:
        """Initialise the genetic code from a genetic code."""
        self._e_count = GC_["_e_count"]
        self._evolvability = GC_["_evolvability"]
        self._reference_count = GC_["_reference_count"]
        self.ancestor_a = GC_["ancestor_a"]
        self.ancestor_b = GC_["ancestor_b"]
        self.e_count = GC_["e_count"]
        self.evolvability = GC_["evolvability"]
        self.f_count = GC_["f_count"]
        self.fitness = GC_["fitness"]
        self.gca = GC_["gca"]
        self.gcb = GC_["gcb"]
        self.graph = GC_["graph"]
        self.pgc = GC_["pgc"]
        self.reference_count = GC_["reference_count"]
        self.survivability = GC_["survivability"]

class aAGC(eGC):
    """Embryonic genetic code class (Application Layer).
    
    Defines the minimal set of fields required to add a genetic code to the genetic code cache using
    self contained data i.e. no links to genetic_code type objects in the cache.
    Too add to the cache genetic code dependencies (signature fields) must already be in the cache.

    Uses strict typing (rather than kwargs) to ensure the genetic code is complete.
    """

    def __init__(self,
        _e_count: int = 1,
        _evolvability: float = 1.0,
        _reference_count: int = 0,
        ancestor_a: bytes | None = None,
        ancestor_b: bytes | None = None,
        e_count: int = 1,
        evolvability: float = 1.0,
        f_count: int = 0,
        fitness: float = 1.0,
        gca: bytes | None = None,
        gcb: bytes | None = None,
        graph: JSONGraph = {},
        pgc: bytes | None = None,
        properties: int = 0,
        reference_count: int = 0,
        survivability: float = 1.0,
    ) -> None:
        """Initialise the genetic code."""
