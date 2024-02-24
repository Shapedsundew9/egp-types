"""The graph module.

# Graph

The graph class is a collection of rows and connections between the rows.
"""

from __future__ import annotations

from logging import DEBUG, Logger, NullHandler, getLogger
from random import seed
from typing import cast

from .connections import connections, EMPTY_CONNECTIONS
from .egp_typing import ALL_ROWS_STR, ROWS, ROWS_INDEXED, DestinationRow, DstRowIndex, EndPointType, JSONGraph, Row, SrcRowIndex
from .ep_type import EP_TYPE_VALUES_TUPLE
from ._genetic_code import _genetic_code, EMPTY_GENETIC_CODE
from .mermaid_charts import MERMAID_IGRAPH_CLASS_DEF_STR, MERMAID_IGRAPH_COLORS
from .rows import rows, EMPTY_ROWS
from .interface import EMPTY_INTERFACE, interface

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class graph:
    """A graph is a collection of rows and connections between the rows."""

    def __init__(self, json_graph: JSONGraph, **kwargs) -> None:
        """Initialize the graph from a JSON graph and GCA & GCB genetic code instances unless rndm is True.
        If rndm is True then the graph is initialised with random (valid) data. The following keyword
        arguments are supported:
        - rndm: bool = False: If True then the graph is initialised with random (valid) data.
        - rseed: int = None: The random seed to use if rndm is True.
        - rows: str = ALL_ROWS_STR: The rows to use if rndm is True.
        - ep_types: tuple[EndPointType, ...] = EP_TYPE_VALUES_TUPLE: The endpoint types to use if rndm is True.
        - max_eps: int = 8: The maximum number of endpoints to use if rndm is True.
        - verify: bool = True: If True then the graph is verified after initialisation.
        """
        io: tuple[interface, interface] = kwargs.get("io", (EMPTY_INTERFACE, EMPTY_INTERFACE))
        if kwargs.get("rndm", False):
            if kwargs.get("rseed", None) is not None:
                seed(kwargs["rseed"])
            rows_str: str = kwargs.get("rows", ALL_ROWS_STR)
            ep_types: tuple[EndPointType, ...] = kwargs.get("ep_types", EP_TYPE_VALUES_TUPLE)
            max_eps: int = kwargs.get("max_eps", 8)
            verify: bool = kwargs.get("verify", False)
            self.rows: rows = rows({})
            self.rows.random(rows_str, max_eps, ep_types, io)
            self.connections: connections = connections({}, _rndm=[self.rows])
            if verify:
                self.assertions()
        elif json_graph:
            gca: _genetic_code = kwargs.get("gca", EMPTY_GENETIC_CODE)
            gcb: _genetic_code = kwargs.get("gcb", EMPTY_GENETIC_CODE)
            self.rows: rows = rows(json_graph=json_graph, gca=gca, gcb=gcb, io=io)
            self.connections: connections = connections(json_graph=json_graph)
        else:
            self.rows = EMPTY_ROWS
            self.connections = EMPTY_CONNECTIONS

    def __repr__(self) -> str:
        """Return the string representation of the graph data."""
        return "\n".join((repr(self.rows), repr(self.connections)))

    def __str__(self) -> str:
        """Return the Mermaid Chart representation of the graph."""
        return "\n".join(self.mermaid()[0])

    def __eq__(self, __value: object) -> bool:
        """Return True if the graph is equal to the value."""
        if not isinstance(__value, graph):
            return False
        return self.rows == __value.rows and self.connections == __value.connections

    def __hash__(self) -> int:
        """Return the hash of the graph."""
        return hash((hash(self.rows), hash(self.connections)))

    def json_graph(self) -> JSONGraph:
        """Return the JSON graph representation of the graph."""
        json_graph: JSONGraph = {}
        for dri in filter(lambda x: self.rows.valid(x), DstRowIndex):  # pylint: disable=unnecessary-lambda
            json_graph[cast(DestinationRow, ROWS_INDEXED[dri])] = [
                [ROWS_INDEXED[sri], int(si), int(self.rows[dri][di])] for sri, _, si, di in self.connections.get_dst_connections(dri).T
            ]
        if self.rows.valid(SrcRowIndex.C):
            json_graph["C"] = [[val, int(typ)] for val, typ in zip(self.rows[SrcRowIndex.C].values, self.rows[SrcRowIndex.C])]
        return json_graph

    def mermaid(self, uid: int = 0) -> tuple[list[str], list[str]]:
        """Return the mermaid charts list of strings for the graph.
        If uid != 0 (the default) then 'uid' in the interface mermaid strings is replaced with
        the zero extended unsigned 16 bit hexadecimal representation of uid and the rows wrapped
        in a subgraph with the same uid. This allows multiple graphs to be displayed in the same
        mermaid chart without name clashes. ([rows], [connections]) is returned.

        Id uid == 0 then the 'uid' string is removed and the rows + connections are wrapped in a
        flowchart. ([flowchart], []) is returned.
        """
        if uid:
            rows_str_list: list[str] = (
                [f"subgraph uid{uid:04x}", "\tdirection TB"]
                + ["\t" + s.replace("uid", f"uid{uid:x04}") for s in self.rows.mermaid()]
                + ["end"]
            )
            return rows_str_list, [s.replace("uid", f"uid{uid:04x}") for s in self.connections.mermaid()]
        header_list: list[str] = ["---", f"Graph instance {id(self)}", "---", "flowchart TB"]
        rows_str_list = ["\t" + s.replace("uid", "") for s in self.rows.mermaid()]
        cstr_list: list[str] = self.connections.mermaid()
        link_list: dict[Row, list[str]] = {row: [str(idx) for idx, cstr in enumerate(cstr_list) if cstr[3] == row] for row in ROWS}
        connections_str_list: list[str] = ["\t" + s.replace("uid", "") for s in cstr_list]
        classes_list: list[str] = ["\t" + s for s in MERMAID_IGRAPH_CLASS_DEF_STR]
        linkstyle_list: list[str] = [
            f"\tlinkStyle {','.join(link_list[row])} color:{MERMAID_IGRAPH_COLORS[row]['link']}" for row in ROWS if link_list[row]
        ]
        return header_list + rows_str_list + connections_str_list + [""] + linkstyle_list + [""] + classes_list, []

    def get_interface(self, iface: str = "IO") -> tuple[interface, interface]:
        """Return the source and destination interfaces."""
        _rows: rows = self.rows
        if iface == "IO":
            return self.get_io()
        if iface == "A":
            return _rows[SrcRowIndex.A], _rows[DstRowIndex.A]
        if iface == "B":
            return _rows[SrcRowIndex.B], _rows[DstRowIndex.B]
        assert False, f"Unknown interface {iface}"

    def get_io(self) -> tuple[interface, interface]:
        """Return the IO interface."""
        return self.rows[SrcRowIndex.I], self.rows[DstRowIndex.O]

    def assertions(self) -> None:
        """Run the assertions for the graph."""
        try:
            self.rows.assertions()
            self.connections.assertions()

            # Ensure connection indicies and types are correct
            for sr, dr, si, di in self.connections.T:
                assert si < len(self.rows[sr]), f"Connection {ROWS_INDEXED[sr]}{si} source index out of range"
                assert di < len(self.rows[dr]), f"Connection {ROWS_INDEXED[dr]}{di} destination index out of range"
                assert (
                    self.rows[sr][si] == self.rows[dr][di]
                ), f"Connection {ROWS_INDEXED[sr]}{si}->{ROWS_INDEXED[dr]}{di} types do not match"
        except AssertionError as e:
            _logger.error(f"Graph assertions failed: {e}")
            _logger.error(f"Graph data:\n{repr(self)}")
            raise e


EMPTY_GRAPH = graph({})