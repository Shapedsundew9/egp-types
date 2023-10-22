"""The internal_graph class."""

from typing import Generator, Iterable, Literal
from itertools import count
from copy import deepcopy

from .egp_typing import (
    DestinationRow,
    EndPointClass,
    EndPointHash,
    EndPointType,
    Row,
    SourceRow,
    DST_EP,
    SrcEndPointHash,
    DstEndPointHash,
)
from .end_point import (
    dst_end_point,
    end_point,
    isDstEndPoint,
    isSrcEndPoint,
    src_end_point,
)


# Compound types
EndPointDict = dict[EndPointHash, end_point]
SrcEndPointDict = dict[SrcEndPointHash, src_end_point]
DstEndPointDict = dict[DstEndPointHash, dst_end_point]


class internal_graph(EndPointDict):
    """Convinient structure for GC graph manipulation."""

    # TODO: Be clear on rules regarding which method modify the structure

    def next_idx(self, row: Row, cls: EndPointClass) -> int:
        """Return the next endpoint index for the class in the row."""
        return len(tuple(self.row_cls_filter(row, cls)))

    def cls_filter(self, cls: EndPointClass) -> Generator[end_point, None, None]:
        """Return all the end points in with cls cls."""
        return (ep for ep in self.values() if ep.cls == cls)

    def dst_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points."""
        return (ep for ep in self.values() if isDstEndPoint(ep))

    def src_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points."""
        return (ep for ep in self.values() if isSrcEndPoint(ep))

    def row_filter(self, row: Row) -> Generator[end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row)

    def row_cls_filter(self, row: Row, cls: EndPointClass) -> Generator[end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row and ep.cls == cls)

    def rows_filter(self, rows: Iterable[Row]) -> Generator[end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row in rows)

    def dst_row_filter(self, row: Row) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points in a row."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row == row)

    def src_row_filter(self, row: Row) -> Generator[src_end_point, None, None]:
        """Return all the source end points in a row."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row == row)

    def dst_rows_filter(self, rows: Iterable[DestinationRow]) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points in the specified rows."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row in rows)

    def src_rows_filter(self, rows: Iterable[SourceRow]) -> Generator[src_end_point, None, None]:
        """Return all the source end points in the specified rows."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row in rows)

    def dst_unref_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points that are unreferenced."""
        return (ep for ep in self.values() if not ep.refs and ep.row != "U" and isDstEndPoint(ep))

    def src_unref_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points that are unreferenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and not ep.refs)

    def dst_ref_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points that are referenced."""
        return (ep for ep in self.values() if ep.row != "U" and ep.refs and isDstEndPoint(ep))

    def src_ref_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points that are referenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.refs)

    def num_eps(self, row: Row, cls: EndPointClass) -> int:
        """Count the endpoint of class cls in a specific row."""
        return sum(ep.cls == cls and ep.row == row for ep in self.values())

    def copy_row(self, row: Row, clean: bool = False) -> EndPointDict:
        """Return a copy of the specified row endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if ep.row == row}

    def copy_rows(self, rows: Iterable[Row], clean: bool = False) -> EndPointDict:
        """Return a copy of the specified rows endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if ep.row in rows}

    def copy_rows_src_eps(self, rows: Iterable[Row], clean: bool = False) -> SrcEndPointDict:
        """Return a copy of the specified rows source endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if isSrcEndPoint(ep) and ep.row in rows}

    def copy_rows_dst_eps(self, rows: Iterable[Row], clean: bool = False) -> DstEndPointDict:
        """Return a copy of the specified rows destination endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if isDstEndPoint(ep) and ep.row in rows}

    def move_row(self, f_row: Row, t_row: Row, clean: bool = False, has_f: bool = False) -> EndPointDict:
        """Return a copy of the specified f_row endpoints mapped to t_row. Remove references if clean is True."""
        return {n.key(): n for n in (ep.move_copy(t_row, clean, has_f) for ep in self.values() if ep.row == f_row)}

    def move_row_cls(
        self,
        f_row: Row,
        f_cls: EndPointClass,
        t_row: Row,
        t_cls: EndPointClass,
        clean: bool = False,
        has_f: bool = False,
    ) -> EndPointDict:
        """Return a copy of the specified f_row & f_cls endpoints mapped to t_row & t_cls. Remove references if clean is True."""
        return {
            n.key(): n
            for n in (ep.move_cls_copy(t_row, t_cls, clean, has_f) for ep in self.values() if ep.row == f_row and ep.cls == f_cls)
        }

    def direct_connect(self, src_row: SourceRow, dst_row: DestinationRow) -> DstEndPointDict:
        """Create a destination row with the exact endpoints needed by src_row."""
        return {n.key(): n for n in (dst_end_point(dst_row, ep.idx, ep.typ) for ep in self.src_row_filter(src_row))}

    def append_connect(self, src_row: SourceRow, dst_row: DestinationRow) -> DstEndPointDict:
        """Create endpoints as they would append to a destination row with the exact endpoints needed by src_row."""
        idx = count(self.next_idx(dst_row, DST_EP))
        return {n.key(): n for n in (dst_end_point(dst_row, next(idx), ep.typ) for ep in self.src_row_filter(src_row))}

    def redirect_refs(self, row: Row, cls: EndPointClass, old_ref_row: Row, new_ref_row: Row) -> None:
        """Redirects cls end point references on row from old_ref_row to new_ref_row."""
        for ep in self.row_cls_filter(row, cls):
            ep.redirect_refs(old_ref_row, new_ref_row)

    def insert_row_as(self, row: Literal["A", "B"]) -> EndPointDict:
        """Create a row with the input & output interface of self."""
        io_if: Generator[end_point, None, None] = self.rows_filter(("I", "O"))
        return {n.key(): n for n in (end_point(row, ep.idx, ep.typ, not ep.cls, deepcopy(ep.refs)) for ep in io_if)}

    def complete_references(self) -> None:
        """An incomplete reference is when a destination references a source but the source does not reference the destination."""
        for dst_ep in self.dst_ref_filter():
            self[dst_ep.refs[0].key()].safe_add_ref(dst_ep.as_ref())
