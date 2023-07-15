"""End point and end point reference classes."""

from dataclasses import dataclass, field
from typing import Any, TypeGuard, Self
from copy import deepcopy

from .egp_typing import (DST_EP, SRC_EP, DestinationRow, DstEndPointHash,
                         EndPointClass, EndPointHash, EndPointIndex,
                         EndPointType, Row, SourceRow, SrcEndPointHash,
                        VALID_ROW_DESTINATIONS, VALID_ROW_SOURCES)


@dataclass(slots=True)
class generic_end_point():
    """Lowest common denominator end point class """
    row: Row
    idx: EndPointIndex

    def key_base(self) -> str:
        """Base end point hash."""
        return f"{self.row}{self.idx:03d}"


@dataclass(slots=True)
class end_point_ref(generic_end_point):
    """Defines the connection to a row in an InternalGraph."""

    def force_key(self, cls: EndPointClass) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'ds'[cls]

    def __eq__(self, ref: Self) -> bool:
        """Equivilence for end point references."""
        return self.row == ref.row and self.idx == ref.idx


@dataclass(slots=True)
class dst_end_point_ref(end_point_ref):
    """Refers to a destination end point"""
    row: DestinationRow

    def __hash__(self) -> int:
        """For hashable operations."""
        return hash(self.key())

    def key(self) -> DstEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'd'

    def invert_key(self) -> SrcEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + 's'


@dataclass(slots=True)
class src_end_point_ref(end_point_ref):
    """Refers to a source endpoint"""
    row: SourceRow

    def __hash__(self) -> int:
        """For hashable operations."""
        return hash(self.key())

    def key(self) -> SrcEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 's'

    def invert_key(self) -> DstEndPointHash:
        """Invert hash. Return a hash for the destination endpoint equivilent."""
        return self.key_base() + 'd'


@dataclass(slots=True)
class end_point(generic_end_point):
    """Defines a end point in a gc_graph.

    If row == 'C', the constants row, then val is set to the constant.
    """
    typ: EndPointType
    cls: EndPointClass
    refs: list[end_point_ref] = field(default_factory=list)
    val: Any = None

    def __hash__(self) -> int:
        """For hashable operations."""
        return hash(self.key())

    def _del_invalid_refs(self, ep: Self, row: Row, has_f: bool = False) -> None:
        """Remove any invalid references"""
        valid_ref_rows: tuple[Row, ...] = VALID_ROW_SOURCES[has_f][row] if ep.cls == DST_EP else VALID_ROW_DESTINATIONS[has_f][row]
        for vidx in reversed([idx for idx, ref in enumerate(ep.refs) if ref.row not in valid_ref_rows]):
            del ep.refs[vidx]

    def key(self) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'ds'[self.cls]

    def force_key(self, force_class: EndPointClass | None = None) -> EndPointHash:
        """Create a unique key to use in the internal graph forcing the class type."""
        cls: str = 'ds'[self.cls] if force_class is None else 'ds'[force_class]
        return self.key_base() + cls

    def as_ref(self) -> end_point_ref:
        """Return a reference to this end point."""
        return end_point_ref(self.row, self.idx)

    def copy(self, clean: bool = False) -> Self:
        """Return a copy of the end point with no references."""
        return end_point(self.row, self.idx, self.typ, self.cls) if clean else deepcopy(self)

    def move_copy(self, row: Row, clean: bool = False, has_f: bool = False) -> Self:
        """Return a copy of the end point with the row changed.
        
        Any references that are no longer valid are deleted.
        """
        ep: Self = self.copy(clean)
        ep.row = row
        if not clean:
            self._del_invalid_refs(ep, row, has_f)
        return ep

    def move_cls_copy(self, row: Row, cls: EndPointClass, clean: bool = False, has_f: bool = False) -> Self:
        """Return a copy of the end point with the row & cls changed."""
        ep: Self = self.copy(clean)
        ep.row = row
        ep.cls = cls
        if not clean:
            self._del_invalid_refs(ep, row, has_f)
        return ep

    def redirect_refs(self, old_ref_row, new_ref_row) -> None:
        """Redirect all references to old_ref_row to new_ref_row."""
        for ref in filter(lambda x: x.row == old_ref_row, self.refs):
            ref.row = new_ref_row

    def safe_add_ref(self, ref: end_point_ref) -> None:
        """Check if a reference exists before adding it."""
        if ref not in self.refs:
            self.refs.append(ref)


@dataclass(slots=True)
class dst_end_point(end_point):
    """Destination End Point."""
    row: DestinationRow
    cls: EndPointClass = DST_EP
    refs: list[src_end_point_ref] = field(default_factory=list)

    def key(self) -> DstEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'd'

    def invert_key(self) -> SrcEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + 's'

    def as_ref(self) -> dst_end_point_ref:
        """Return a reference to this end point."""
        return dst_end_point_ref(self.row, self.idx)

    def clean_copy(self) -> Self:
        """Return a copy of the end point with no references."""
        return dst_end_point(self.row, self.idx, self.typ)


@dataclass(slots=True)
class src_end_point(end_point):
    """Source End Point."""
    row: SourceRow
    cls: EndPointClass = SRC_EP
    refs: list[dst_end_point_ref] = field(default_factory=list)

    def key(self) -> SrcEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 's'

    def invert_key(self) -> DstEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + 'd'

    def as_ref(self) -> src_end_point_ref:
        """Return a reference to this end point."""
        return src_end_point_ref(self.row, self.idx)

    def clean_copy(self) -> Self:
        """Return a copy of the end point with no references."""
        return src_end_point(self.row, self.idx, self.typ)


def isDstEndPoint(ep: end_point) -> TypeGuard[dst_end_point]:
    """Identifies an end point as a destination endpoint."""
    return not ep.cls


def isSrcEndPoint(ep: end_point) -> TypeGuard[src_end_point]:
    """Identifies an end point as a source endpoint."""
    return ep.cls
