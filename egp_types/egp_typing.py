"""Common Erasmus GP Types."""
from dataclasses import dataclass
from typing import Callable, Iterable, Literal, Any, TypeGuard, Generator
from enum import IntEnum
from graph_tool import Vertex as gt_vertex
from graph_tool import Edge as gt_edge

from .xGC import xGC

FitnessFunction = Callable[[Iterable[xGC]], None]
SurvivabilityFunction = Callable[[Iterable[xGC], Iterable[xGC]], None]

DestinationRow = Literal['A', 'B', 'F', 'O', 'P', 'U']
SourceRow = Literal['I', 'C', 'A', 'B']
Row = Literal['A', 'B', 'F', 'O', 'P', 'I', 'C', 'A', 'B', 'U']
EndPointClass = bool
EndPointIndex = int
EndPointType = int
EndPointHash = str

# TODO: Can GCGraphRows be constrained further to tuple[dict[DestinationRow, int], dict[SourceRow, int]]
GCGraphRows = tuple[dict[str, int], dict[str, int]]


# Constants
SRC_EP: Literal[True] = True
DST_EP: Literal[False] = False
DESTINATION_ROWS: tuple[DestinationRow, ...] = ('A', 'B', 'F', 'O', 'P', 'U')
SOURCE_ROWS: tuple[SourceRow, ...] = ('I', 'C', 'A', 'B')
ROWS: tuple[Row, ...] = tuple(sorted((*SOURCE_ROWS, *DESTINATION_ROWS)))
VALID_ROW_SOURCES: dict[Row, tuple[SourceRow, ...]] = {
    'I': tuple(),
    'C': tuple(),
    'A': ('I', 'C'),
    'B': ('I', 'C', 'A'),
    'U': ('I', 'C', 'A', 'B'),
    'O': ('I', 'C', 'A', 'B'),
    'P': ('I', 'C', 'B'),
    'F': ('I',)
}


def isDestinationRow(obj) -> TypeGuard[DestinationRow]:
    """Test if obj is of DestinationRow type."""
    return obj in DESTINATION_ROWS


def isSourceRow(obj) -> TypeGuard[SourceRow]:
    """Test if obj is of SourceRow type."""
    return obj in SOURCE_ROWS


def isRow(obj) -> TypeGuard[Row]:
    """Test if obj is of Row type."""
    return obj in ROWS


def castDestinationRow(obj) -> DestinationRow:
    """Force obj to DestinationRow type or raise a type exception."""
    if isDestinationRow(obj):
        return obj
    raise TypeError('obj should always be type DestinationRow compatible.')


def castSourceRow(obj) -> SourceRow:
    """Force obj to SourceRow type or raise a type exception."""
    if isSourceRow(obj):
        return obj
    raise TypeError('obj should always be type SourceRow compatible.')


def castRow(obj) -> Row:
    """Force obj to Row type or raise a type exception."""
    if isRow(obj):
        return obj
    raise TypeError('obj should always be type Row compatible.')


def castEndPointIndex(obj) -> EndPointIndex:
    """Force obj to EndPointIndex type or raise a type exception."""
    if isinstance(obj, EndPointIndex):
        return obj
    raise TypeError('obj should always be type EndPointIndex compatible.')


def castEndPointType(obj) -> EndPointType:
    """Force obj to EndPointType type or raise a type exception."""
    if isinstance(obj, EndPointType):
        return obj
    raise TypeError('obj should always be type EndPointType compatible.')


class CPI(IntEnum):
    """Indices into a ConnectionPoint."""
    ROW = 0
    IDX = 1
    TYP = 2
    CTYP = 0
    CVAL = 1


# ConnectionPoint has to be a list rather than a tuple as it has to be JSON compatible
ConnectionPoint = list[Row | EndPointIndex | EndPointType | Any]
ConnectionGraphRow = list[ConnectionPoint]
ConnectionGraph = dict[Row, ConnectionGraphRow]


ConnectionGraphRow = list[ConnectionPoint]
ConnectionGraph = dict[Row, ConnectionGraphRow]


class Vertex(gt_vertex):
    """Static type checking cannot follow the graph_tool Vertex class."""


class Edge(gt_edge):
    """Static type checking cannot follow the graph_tool Edge class."""


@dataclass(slots=True)
class GenericEndPoint():
    """Lowest common denominator end point class """
    row: Row
    idx: EndPointIndex

    def key_base(self) -> str:
        """Base end point hash."""
        return f"{self.row}{self.idx:03d}"


@dataclass(slots=True)
class EndPointReference(GenericEndPoint):
    """Defines the connection to a row in an InternalGraph."""

    def key(self, cls: EndPointClass) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'ds'[cls]


@dataclass(slots=True)
class DstEndPointReference(EndPointReference):
    """Refers to a destination end point"""
    row: DestinationRow

    def key(self, _: EndPointClass = DST_EP) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'd'


@dataclass(slots=True)
class SrcEndPointReference(EndPointReference):
    """Refers to a source endpoint"""
    row: SourceRow

    def key(self, _: EndPointClass = SRC_EP) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 's'


@dataclass(slots=True)
class EndPoint(GenericEndPoint):
    """Defines a end point in a gc_graph.

    If row == 'C', the constants row, then val is set to the constant.
    """
    typ: EndPointType
    cls: EndPointClass
    refs: list[EndPointReference] = []
    val: Any = None

    def key(self, force_class: EndPointClass | None = None) -> EndPointHash:
        """Create a unique key to uise in the internal graph."""
        cls: str = 'ds'[self.cls] if force_class is None else 'ds'[force_class]
        return self.key_base() + cls 


@dataclass(slots=True)
class DstEndPoint(EndPoint):
    """Destination End Point."""
    row: DestinationRow
    refs: list[SrcEndPointReference]
    cls: EndPointClass = DST_EP


@dataclass(slots=True)
class SrcEndPoint(EndPoint):
    """Source End Point."""
    row: SourceRow
    refs: list[DstEndPointReference]
    cls: EndPointClass = SRC_EP


def isDstEndPoint(ep: EndPoint) -> TypeGuard[DstEndPoint]:
    """Identifies an end point as a destination endpoint."""
    return not ep.cls


def isSrcEndPoint(ep: EndPoint) -> TypeGuard[SrcEndPoint]:
    """Identifies an end point as a source endpoint."""
    return ep.cls


class InternalGraph(dict[EndPointHash, EndPoint]):
    """Convinient structure for GC graph manipulation."""

    def dst_filter(self) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points."""
        return (ep for ep in self.values() if isDstEndPoint(ep))

    def src_filter(self) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points."""
        return (ep for ep in self.values() if isSrcEndPoint(ep))

    def row_filter(self, row) -> Generator[EndPoint, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row)

    def dst_row_filter(self, row) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points in row."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row == row)

    def src_row_filter(self, row) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points in row."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row == row)
