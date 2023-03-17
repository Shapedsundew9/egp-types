"""Common Erasmus GP Types."""
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal, Any, TypeGuard, Generator, TypedDict, NotRequired
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
SrcEndPointHash = str
DstEndPointHash = str
EndPointHash = SrcEndPointHash | DstEndPointHash | str

# TODO: Can GCGraphRows be constrained further to tuple[dict[DestinationRow, int], dict[SourceRow, int]]
GCGraphRows = tuple[dict[str, int], dict[str, int]]


# Constants
SRC_EP: Literal[True] = True
DST_EP: Literal[False] = False
DESTINATION_ROWS: tuple[DestinationRow, ...] = ('A', 'B', 'F', 'O', 'P', 'U')
SOURCE_ROWS: tuple[SourceRow, ...] = ('I', 'C', 'A', 'B')
ROWS: tuple[Row, ...] = tuple(sorted((*SOURCE_ROWS, *DESTINATION_ROWS)))

# Valid source rows for a given row.
# The valid source rows depends on whether there is a row F
VALID_ROW_SOURCES: tuple[dict[Row, tuple[SourceRow, ...]], dict[Row, tuple[SourceRow, ...]]] = (
    # No row F
    {
        'I': tuple(),
        'C': tuple(),
        'A': ('I', 'C'),
        'B': ('I', 'C', 'A'),
        'U': ('I', 'C', 'A', 'B'),
        'O': ('I', 'C', 'A', 'B'),
        'P': ('I', 'C', 'B'),
        'F': ('I',)
    },
    # Has row F
    # F determines if the path through A or B is chosen
    {
        'I': tuple(),
        'C': tuple(),
        'A': ('I', 'C'),
        'B': ('I', 'C'),
        'O': ('I', 'C', 'A'),
        'U': ('I', 'C', 'A', 'B'),
        'P': ('I', 'C', 'B'),
        'F': ('I',)
    }
)


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


class CVI(IntEnum):
    """Indices into a ConstantValue."""
    TYP = 0
    VAL = 1


class PairIdx(IntEnum):
    """Indices into *Pair."""
    ROW = 0
    VALUES = 1


# A ConnectionGraph is the graph defined in the GC GMS.
# It is a dict of Destination Rows (or constant value row - which makes things a bit more awkward)
# with a list of the Source row references + type that connect to it.
ConnectionPoint = tuple[SourceRow, EndPointIndex, EndPointType]
ConnectionRow = list[ConnectionPoint]
ConstantExecStr = str
ConstantValue = tuple[EndPointType, ConstantExecStr]
ConstantRow = list[ConstantValue]
ConnectionGraphPair = tuple[DestinationRow | Literal['C'], ConnectionRow | ConstantRow]
ConnectionPair = tuple[DestinationRow, ConnectionRow]
ConstantPair = tuple[Literal['C'], ConstantRow]


class ConnectionGraph(TypedDict):
    A: NotRequired[ConnectionRow]
    B: NotRequired[ConnectionRow]
    C: NotRequired[ConstantRow]
    F: NotRequired[ConnectionRow]
    O: NotRequired[ConnectionRow]
    P: NotRequired[ConnectionRow]
    U: NotRequired[ConnectionRow]


def isConstantPair(obj: tuple[str, Any]) -> TypeGuard[ConstantPair]:
    """Narrow a connection graph key:value pair to either a constant row."""
    return obj[0] == 'C'


def isConnectionPair(obj: tuple[str, Any]) -> TypeGuard[ConnectionPair]:
    """Narrow a connection graph key:value pair to either a connection row."""
    return obj[0] != 'C'


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

    def force_key(self, cls: EndPointClass) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'ds'[cls]


@dataclass(slots=True)
class DstEndPointReference(EndPointReference):
    """Refers to a destination end point"""
    row: DestinationRow

    def key(self) -> DstEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'd'

    def invert_key(self) -> SrcEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + 's'


@dataclass(slots=True)
class SrcEndPointReference(EndPointReference):
    """Refers to a source endpoint"""
    row: SourceRow

    def key(self) -> SrcEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 's'

    def invert_key(self) -> DstEndPointHash:
        """Invert hash. Return a hash for the destination endpoint equivilent."""
        return self.key_base() + 'd'


@dataclass(slots=True)
class EndPoint(GenericEndPoint):
    """Defines a end point in a gc_graph.

    If row == 'C', the constants row, then val is set to the constant.
    """
    typ: EndPointType
    cls: EndPointClass
    refs: list[EndPointReference] = field(default_factory=list)
    val: Any = None

    def key(self) -> EndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'ds'[self.cls]

    def force_key(self, force_class: EndPointClass | None = None) -> EndPointHash:
        """Create a unique key to use in the internal graph forcing the class type."""
        cls: str = 'ds'[self.cls] if force_class is None else 'ds'[force_class]
        return self.key_base() + cls


@dataclass(slots=True)
class DstEndPoint(EndPoint):
    """Destination End Point."""
    row: DestinationRow
    cls: EndPointClass = DST_EP
    refs: list[SrcEndPointReference] = field(default_factory=list)

    def key(self) -> DstEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 'd'

    def invert_key(self) -> SrcEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + 's'


@dataclass(slots=True)
class SrcEndPoint(EndPoint):
    """Source End Point."""
    row: SourceRow
    cls: EndPointClass = SRC_EP
    refs: list[DstEndPointReference] = field(default_factory=list)

    def key(self) -> SrcEndPointHash:
        """Create a unique key to use in the internal graph."""
        return self.key_base() + 's'

    def invert_key(self) -> DstEndPointHash:
        """Invert hash. Return a hash for the source endpoint equivilent."""
        return self.key_base() + 'd'


def isDstEndPoint(ep: EndPoint) -> TypeGuard[DstEndPoint]:
    """Identifies an end point as a destination endpoint."""
    return not ep.cls


def isSrcEndPoint(ep: EndPoint) -> TypeGuard[SrcEndPoint]:
    """Identifies an end point as a source endpoint."""
    return ep.cls


class InternalGraph(dict[EndPointHash, EndPoint]):
    """Convinient structure for GC graph manipulation."""

    def cls_filter(self, cls: EndPointClass) -> Generator[EndPoint, None, None]:
        """Return all the end points in with cls cls."""
        return (ep for ep in self.values() if ep.cls == cls)

    def dst_filter(self) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points."""
        return (ep for ep in self.values() if isDstEndPoint(ep))

    def src_filter(self) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points."""
        return (ep for ep in self.values() if isSrcEndPoint(ep))

    def row_filter(self, row: Row) -> Generator[EndPoint, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row)

    def rows_filter(self, rows: Iterable[Row]) -> Generator[EndPoint, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row in rows)

    def dst_row_filter(self, row: Row) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points in a row."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row == row)

    def src_row_filter(self, row: Row) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points in a row."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row == row)

    def dst_rows_filter(self, rows: Iterable[DestinationRow]) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points in the specified rows."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row in rows)

    def src_rows_filter(self, rows: Iterable[SourceRow]) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points in the specified rows."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row in rows)

    def dst_unref_filter(self) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points that are unreferenced."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and not ep.refs)

    def src_unref_filter(self) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points that are unreferenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and not ep.refs)

    def dst_ref_filter(self) -> Generator[DstEndPoint, None, None]:
        """Return all the destination end points that are referenced."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.refs)

    def src_ref_filter(self) -> Generator[SrcEndPoint, None, None]:
        """Return all the source end points that are referenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.refs)

    def num_eps(self, row: Row, cls: EndPointClass) -> int:
        """Count the endpoint of class cls in a specific row."""
        return sum(ep.cls == cls and ep.row == row for ep in self.values())


class EndPointTypeLookupFile(TypedDict):
    """Format of the egp_type.json file."""
    n2v: dict[str, int]
    v2n: dict[str, str]
    instanciation: dict[str, list[str | bool | None]]


def isInstanciationValue(obj) -> TypeGuard[tuple[str | None, str | None, str | None, str | None, bool]]:
    """Is obj an instance of an instanciation definition."""
    if not isinstance(obj, tuple):
        return False
    if not len(obj) == 5:
        return False
    if not all((isinstance(element, str) or element is None for element in obj[:4])):
        return False
    return isinstance(bool, obj[4])


class EndPointTypeLookup(TypedDict):
    """Format of the ep_type_lookup structure."""
    n2v: dict[str, int]  # End point type name: End point type value
    v2n: dict[int, str]  # End point type value: End point type name

    # End point type value: package, version, module, name, can take parameters
    instanciation: dict[int, tuple[str | None, str | None, str | None, str | None, bool]]
