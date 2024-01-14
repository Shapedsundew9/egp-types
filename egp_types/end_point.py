"""End point and end point reference classes."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TypeGuard, Self, cast
from copy import deepcopy
from logging import DEBUG, Logger, NullHandler, getLogger

from .egp_typing import (
    DST_EP,
    SRC_EP,
    DestinationRow,
    DstEndPointHash,
    EndPointClass,
    EndPointHash,
    EndPointIndex,
    EndPointType,
    Row,
    SourceRow,
    SrcEndPointHash,
    VALID_ROW_DESTINATIONS,
    VALID_ROW_SOURCES,
    SOURCE_ROWS,
    DESTINATION_ROWS,
)


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


@dataclass(slots=True)
class generic_end_point:
    """Lowest common denominator end point class"""

    row: Row
    idx: EndPointIndex

    def json_obj(self) -> list[str | int]:
        """Return a json serializable object."""
        return [self.row, self.idx]

    def key_base(self) -> str:
        """Base end point hash."""
        return f"{self.row}{self.idx:03d}"


@dataclass(slots=True)
class end_point_ref(generic_end_point):
    """Defines the connection to a row in an InternalGraph."""

    def force_key(self, cls: EndPointClass) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + "ds"[cls]

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
        return self.key_base() + "d"

    def invert_key(self) -> SrcEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + "s"


@dataclass(slots=True)
class src_end_point_ref(end_point_ref):
    """Refers to a source endpoint"""

    row: SourceRow

    def __hash__(self) -> int:
        """For hashable operations."""
        return hash(self.key())

    def key(self) -> SrcEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + "s"

    def invert_key(self) -> DstEndPointHash:
        """Invert hash. Return a hash for the destination endpoint equivilent."""
        return self.key_base() + "d"


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

    def _del_invalid_refs(self, ep: end_point, row: Row, has_f: bool = False) -> None:
        """Remove any invalid references"""
        valid_ref_rows: tuple[Row, ...] = VALID_ROW_SOURCES[has_f][row] if ep.cls == DST_EP else VALID_ROW_DESTINATIONS[has_f][row]
        for vidx in reversed([idx for idx, ref in enumerate(ep.refs) if ref.row not in valid_ref_rows]):
            del ep.refs[vidx]

    def json_obj(self) -> list[str | int | bool | list[list[str | int]] | None]:
        """Return a json serializable object."""
        return [self.row, self.idx, self.typ, self.cls, [ref.json_obj() for ref in self.refs], self.val]

    def key(self) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + "ds"[self.cls]

    def force_key(self, force_class: EndPointClass | None = None) -> EndPointHash:
        """Create a unique key to use in the internal graph forcing the class type."""
        cls: str = "ds"[self.cls] if force_class is None else "ds"[force_class]
        return self.key_base() + cls

    def as_ref(self) -> end_point_ref:
        """Return a reference to this end point."""
        return end_point_ref(self.row, self.idx)

    def copy(self, clean: bool = False) -> Self:
        """Return a copy of the end point with no references."""
        return self.__class__(self.row, self.idx, self.typ, self.cls, val=self.val) if clean else deepcopy(self)

    def move_copy(self, row: Row, clean: bool = False, has_f: bool = False) -> Self:
        """Return a copy of the end point with the row changed.

        Any references that are no longer valid are deleted.
        """
        ep: Self = self.copy(clean)
        ep.row = row
        if not clean:
            self._del_invalid_refs(ep, row, has_f)
        return ep

    def move_cls_copy(self, row: Row, cls: EndPointClass) -> x_end_point:
        """Return a copy of the end point with the row & cls changed."""
        # If the class of the endpoint has changed then the references must be invalid and are not copied.
        if cls == SRC_EP:
            assert row in SOURCE_ROWS, "Invalid row for source endpoint"
            return src_end_point(cast(SourceRow, row), self.idx, self.typ, val=self.val)
        assert row in DESTINATION_ROWS, "Invalid row for destination endpoint"
        return dst_end_point(cast(DestinationRow, row), self.idx, self.typ, val=self.val)

    def redirect_refs(self, old_ref_row, new_ref_row) -> None:
        """Redirect all references to old_ref_row to new_ref_row."""
        for ref in filter(lambda x: x.row == old_ref_row, self.refs):
            ref.row = new_ref_row


@dataclass(slots=True)
class dst_end_point(end_point):
    """Destination End Point."""

    row: DestinationRow
    cls: EndPointClass = DST_EP
    refs: list[src_end_point_ref] = field(default_factory=list)

    def key(self) -> DstEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + "d"

    def invert_key(self) -> SrcEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + "s"

    def as_ref(self) -> dst_end_point_ref:
        """Return a reference to this end point."""
        return dst_end_point_ref(self.row, self.idx)

    def copy(self, clean: bool = False) -> dst_end_point:
        """Return a copy of the end point with no references."""
        return dst_end_point(self.row, self.idx, self.typ, self.cls, val=self.val) if clean else deepcopy(self)

    def clean_copy(self) -> dst_end_point:
        """Return a copy of the end point with no references."""
        return dst_end_point(self.row, self.idx, self.typ)

    def safe_add_ref(self, ref: src_end_point_ref) -> None:
        """Check destination endpoint has a reference before adding it."""
        if not self.refs:
            self.refs.append(ref)
        else:
            # OK if it is the same reference (though inefficient)
            assert self.refs[0] == ref, "Destination endpoint already has a reference."


@dataclass(slots=True)
class src_end_point(end_point):
    """Source End Point."""

    row: SourceRow
    cls: EndPointClass = SRC_EP
    refs: list[dst_end_point_ref] = field(default_factory=list)

    def key(self) -> SrcEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + "s"

    def invert_key(self) -> DstEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + "d"

    def as_ref(self) -> src_end_point_ref:
        """Return a reference to this end point."""
        return src_end_point_ref(self.row, self.idx)

    def copy(self, clean: bool = False) -> src_end_point:
        """Return a copy of the end point with no references."""
        return src_end_point(self.row, self.idx, self.typ, self.cls, val=self.val) if clean else deepcopy(self)

    def clean_copy(self) -> src_end_point:
        """Return a copy of the end point with no references."""
        return src_end_point(self.row, self.idx, self.typ, val=self.val)

    def safe_add_ref(self, ref: dst_end_point_ref) -> None:
        """Check if a reference exists before adding it."""
        if ref not in self.refs:
            _logger.warning(f"Adding reference {ref} to {self}: This is inefficient.")
            self.refs.append(ref)


def isDstEndPoint(ep: end_point) -> TypeGuard[dst_end_point]:
    """Identifies an end point as a destination endpoint."""
    return not ep.cls


def isSrcEndPoint(ep: end_point) -> TypeGuard[src_end_point]:
    """Identifies an end point as a source endpoint."""
    return ep.cls


x_end_point = src_end_point | dst_end_point
x_end_point_ref = src_end_point_ref | dst_end_point_ref
