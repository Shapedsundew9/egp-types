"""The internal_graph class."""

from typing import Generator, Iterable

from .egp_typing import DestinationRow, EndPointClass, EndPointHash, Row, SourceRow
from .end_point import dst_end_point, end_point, isDstEndPoint, isSrcEndPoint, src_end_point


class internal_graph(dict[EndPointHash, end_point]):
    """Convinient structure for GC graph manipulation."""

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
        return (ep for ep in self.values() if isDstEndPoint(ep) and not ep.refs)

    def src_unref_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points that are unreferenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and not ep.refs)

    def dst_ref_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points that are referenced."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.refs)

    def src_ref_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points that are referenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.refs)

    def num_eps(self, row: Row, cls: EndPointClass) -> int:
        """Count the endpoint of class cls in a specific row."""
        return sum(ep.cls == cls and ep.row == row for ep in self.values())
