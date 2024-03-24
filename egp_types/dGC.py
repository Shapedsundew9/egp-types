"""Basic GP dict GC type definitions.

xGCs come in two flavours:
    Application Layer GC's - self contained data using basic python types.
    Gene Pool Cache Layer GC's - linked to genetic_code type objects in the cache but is not in the cache itself.
"""
from __future__ import annotations
from typing import Any
from numpy.typing import NDArray
from numpy import uint8, int32, int64, float32

from egp_types._genetic_code import _genetic_code
from egp_types.internal_graph import internal_graph
from .gc_type_tools import (
    INT32_ONE,
    INT64_ZERO,
    FLOAT32_ZERO,
    FLOAT32_ONE,
    INT32_ZERO,
    app_sig_to_array,
)
from .graph import graph
from ._genetic_code import _genetic_code
from .genetic_code import genetic_code_factory
from .genetic_code_cache import genetic_code_cache
from .eGC import eGC


_DEFAULT_GCC: genetic_code_cache = genetic_code_cache(genetic_code_factory())


class dGC:
    """Default genetic code class (Gene Pool Cache Layer).

    Defines the minimal set of fields required to add a genetic code to the genetic code cache.
    It has the same information as a eGC but all the dependencies are linked to genetic_code type objects and
    types are the same as in the Gene Pool Cache.

    Uses strict typing (rather than kwargs) to ensure the genetic code is complete.
    """

    def __init__(self, gcc: genetic_code_cache = _DEFAULT_GCC, **kwargs) -> None:
        """Initialise the genetic code."""
        self.gcc_: genetic_code_cache = gcc
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
        self.members_ = tuple(m for m in self.__dict__ if not m.endswith("_"))
        if "dGC" in kwargs:
            self.from_dGC(kwargs["dGC"])
        elif "eGC" in kwargs:
            self.from_eGC(kwargs["eGC"])
        elif "GC" in kwargs:
            self.from_GC(kwargs["GC"])
        elif "gc_dict" in kwargs:
            self.from_dict(kwargs["gc_dict"])
        self.igraph_: internal_graph = self.graph.igraph()

    def from_dGC(self, dGC_: dGC) -> None:
        """Initialise the genetic code from a dGC."""
        # TODO: This is an unforeseen clash of convenstions...probably should be a trailing _
        self._e_count = dGC_._e_count  # pylint: disable=protected-access
        self._evolvability = dGC_._evolvability  # pylint: disable=protected-access
        self._reference_count = dGC_._reference_count  # pylint: disable=protected-access
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

    def from_dict(self, gc_dict: dict[str, Any]) -> None:
        """Initialise the genetic code from a dictionary."""
        for key in filter(lambda x: x in gc_dict, self.members_):
            setattr(self, key, gc_dict[key])

    def from_eGC(self, eGC_: eGC) -> None:
        """Initialise the genetic code from a eGC."""
        byte_sigs: tuple[NDArray[uint8], ...] = (
            app_sig_to_array(eGC_.ancestor_a),
            app_sig_to_array(eGC_.ancestor_b),
            app_sig_to_array(eGC_.gca),
            app_sig_to_array(eGC_.gcb),
        )
        gcs: list[_genetic_code] = self.gcc_.find(byte_sigs)
        self.ancestor_a = gcs[0]
        self.ancestor_b = gcs[1]
        self.gca = gcs[2]
        self.gcb = gcs[3]
        self.graph = graph(eGC_.graph)
        # dGC does not store meta_data because it has no use in the cache.

    def from_GC(self, _GC_: _genetic_code) -> None:
        """Initialise the genetic code from a genetic code."""
        self._e_count = _GC_["_e_count"]
        self._evolvability = _GC_["_evolvability"]
        self._reference_count = _GC_["_reference_count"]
        self.ancestor_a = _GC_["ancestor_a"]
        self.ancestor_b = _GC_["ancestor_b"]
        self.e_count = _GC_["e_count"]
        self.evolvability = _GC_["evolvability"]
        self.f_count = _GC_["f_count"]
        self.fitness = _GC_["fitness"]
        self.gca = _GC_["gca"]
        self.gcb = _GC_["gcb"]
        self.graph = _GC_["graph"]
        self.pgc = _GC_["pgc"]
        self.reference_count = _GC_["reference_count"]
        self.survivability = _GC_["survivability"]
