"""Common Erasmus GP Types."""
from typing import Literal, Any, TypeGuard, TypedDict, NotRequired
from enum import IntEnum
from graph_tool import Vertex as gt_vertex
from graph_tool import Edge as gt_edge


DestinationRow = Literal['A', 'B', 'F', 'O', 'P', 'U']
SourceRow = Literal['I', 'C', 'A', 'B']
Row = Literal['A', 'B', 'F', 'O', 'P', 'I', 'C', 'U']
EndPointClass = bool
EndPointIndex = int
EndPointType = int
SrcEndPointHash = str
DstEndPointHash = str
EndPointHash = SrcEndPointHash | DstEndPointHash | str

# TODO: Can GCGraphRows be constrained further to tuple[dict[DestinationRow, int], dict[SourceRow, int]]
GCGraphRows = tuple[dict[Row, int], dict[Row, int]]


# Constants
SRC_EP: Literal[True] = True
DST_EP: Literal[False] = False
DESTINATION_ROWS: tuple[DestinationRow, ...] = ('A', 'B', 'F', 'O', 'P', 'U')
SOURCE_ROWS: tuple[SourceRow, ...] = ('I', 'C', 'A', 'B')
ROWS: tuple[Row, ...] = tuple(sorted({*SOURCE_ROWS, *DESTINATION_ROWS}))

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
        'O': ('I', 'C', 'A', 'B')
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


def isDestinationRow(row: Row) -> TypeGuard[DestinationRow]:
    """Narrow a row to a destination row."""
    return row in DESTINATION_ROWS


# Valid destination rows for a given row.
# The valid destination rows depends on whether there is a row F
VALID_ROW_DESTINATIONS: tuple[dict[Row, tuple[DestinationRow, ...]], dict[Row, tuple[DestinationRow, ...]]] = (
    # No row F
    {k: tuple(d for d, s in VALID_ROW_SOURCES[False].items() if k in s and isDestinationRow(d)) for k in ROWS},
    # Has row F
    # F determines if the path through A or B is chosen
    {k: tuple(d for d, s in VALID_ROW_SOURCES[True].items() if k in s and isDestinationRow(d)) for k in ROWS},
)


class CPI(IntEnum):
    """Indices into a ConnectionPoint."""
    ROW = 0
    IDX = 1
    TYP = 2


class CVI(IntEnum):
    """Indices into a ConstantValue."""
    VAL = 0
    TYP = 1


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
ConstantValue = tuple[ConstantExecStr, EndPointType]
ConstantRow = list[ConstantValue]
ConnectionGraphPair = tuple[DestinationRow | Literal['C'], ConnectionRow | ConstantRow]
ConnectionPair = tuple[DestinationRow, ConnectionRow]
ConstantPair = tuple[Literal['C'], ConstantRow]
JSONGraph = dict[DestinationRow, list[list[SourceRow | EndPointIndex | EndPointType]] | list[list[ConstantExecStr | EndPointType]]]


class ConnectionGraph(TypedDict):
    """The structure of the connection graph (the graph defined in a GMS)."""
    A: NotRequired[ConnectionRow]
    B: NotRequired[ConnectionRow]
    C: NotRequired[ConstantRow]
    F: NotRequired[ConnectionRow]
    O: NotRequired[ConnectionRow]
    P: NotRequired[ConnectionRow]
    U: NotRequired[ConnectionRow]


def json_to_connection_graph(json_graph: JSONGraph) -> ConnectionGraph:
    """convert a JSON connection graph to a ConnectionGraph."""
    return {k: [tuple(e) for e in v] for k, v in json_graph.items()}  # type: ignore


def isConstantPair(obj: tuple[str, Any]) -> TypeGuard[ConstantPair]:
    """Narrow a connection graph key:value pair to a constant row."""
    return obj[0] == 'C'


def isConnectionPair(obj: tuple[str, Any]) -> TypeGuard[ConnectionPair]:
    """Narrow a connection graph key:value pair to a connection row."""
    return obj[0] != 'C'


class vertex(gt_vertex):
    """Static type checking cannot follow the graph_tool Vertex class."""


class edge(gt_edge):
    """Static type checking cannot follow the graph_tool Edge class."""


class EndPointTypeLookupFile(TypedDict):
    """Format of the egp_type.json file."""
    n2v: dict[str, int]
    v2n: dict[str, str]
    instanciation: dict[str, list[str | bool | None]]


def isInstanciationValue(obj) -> TypeGuard[tuple[str | None, str | None, str | None, str | None, bool, str]]:
    """Is obj an instance of an instanciation definition."""
    if not isinstance(obj, (tuple, list)):
        return False
    if not len(obj) == 6:
        return False
    if not all((isinstance(element, str) or element is None for element in obj[:4])):
        return False
    return isinstance(obj[4], bool) and isinstance(obj[5], str)


InstanciationType = tuple[str | None, str | None, str | None, str | None, bool, str]


class EndPointTypeLookup(TypedDict):
    """Format of the ep_type_lookup structure."""
    n2v: dict[str, int]  # End point type name: End point type value
    v2n: dict[int, str]  # End point type value: End point type name

    # End point type value: package, version, module, name, default can take parameters
    instanciation: dict[int, InstanciationType]
