"""Basic dict GC type definition."""
from typing import Required, NotRequired, TypedDict
from .egp_typing import ConnectionGraph
from .gc_graph import gc_graph


class dGC(TypedDict):
    """A dict based minimal GC."""
    graph: NotRequired[ConnectionGraph]
    igraph: Required[gc_graph]
    ancestor_a_ref: Required[int | None]
    ancestor_b_ref: Required[int | None]
    ref: Required[int]
    gca_ref: Required[int | None]
    gcb_ref: Required[int | None]
