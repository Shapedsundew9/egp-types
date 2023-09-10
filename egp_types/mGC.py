"""Minimal dict GC type definition."""
from typing import Required, NotRequired, TypedDict
from .egp_typing import ConnectionGraph


class mGC(TypedDict):
    """A dict based minimal GC."""

    graph: Required[ConnectionGraph]
    ancestor_a: Required[bytes]
    ancestor_b: Required[bytes]
    signature: NotRequired[bytes]
    gca: Required[bytes]
    gcb: Required[bytes]
    creator: Required[int]
