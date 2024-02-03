"""The graph module.

# Graph

The graph class is a collection of rows and connections between the rows.
"""
from .connections import connections
from .egp_typing import JSONGraph
from .rows import rows
from .genetic_code import _genetic_code


class graph:
    """A graph is a collection of rows and connections between the rows."""

    def __init__(self, json_graph: JSONGraph, gca: _genetic_code, gcb: _genetic_code, empty: _genetic_code) -> None:
        self.rows: rows = rows(json_graph=json_graph, gca=gca, gcb=gcb, empty=empty)
        self.connections: connections = connections(json_graph=json_graph)

    def __repr__(self) -> str:
        return '\n'.join(self.mermaid()[0])

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
            rows_str_list: list[str] = [f"subgraph uid{uid:x04}", "\tdirection TB"] + ["\t" + s.replace("uid", f"uid{uid:x04}") for s in self.rows.mermaid()] + ["end"]
            return rows_str_list, [s.replace("uid", f"uid{uid:x04}") for s in self.connections.mermaid()]
        rows_str_list = ["\t" + s.replace("uid", "") for s in self.rows.mermaid()]
        connections_str_list: list[str] = ["\t" + s.replace("uid", "") for s in self.connections.mermaid()]
        return ["flowchart TB"] + rows_str_list + connections_str_list + [""], []
