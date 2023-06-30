"""Basic GP dict GC type definition."""
from typing import Required, NotRequired, TypedDict
from .egp_typing import ConnectionGraph
from .gc_graph import gc_graph


class dGC(TypedDict):
    """A dict based minimal GC."""
    graph: NotRequired[ConnectionGraph]
    vertex_idx: NotRequired[int]
    gc_graph: Required[gc_graph]
    ancestor_a_ref: Required[int]
    ancestor_b_ref: Required[int]
    missing_links_a: NotRequired[int]
    missing_links_b: NotRequired[int]
    lost_descendants: NotRequired[int]
    ref: Required[int]
    gca_ref: Required[int]
    gcb_ref: Required[int]
