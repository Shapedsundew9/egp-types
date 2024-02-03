"""This module contains the graph class."""
from .connections import connections
from .egp_typing import JSONGraph
from .rows import rows
from .genetic_code import _genetic_code


class graph:
    """A graph is a collection of rows and connections between the rows."""

    def __init__(self, json_graph: JSONGraph, gca: _genetic_code, gcb: _genetic_code, empty: _genetic_code) -> None:
        self.row: rows = rows(json_graph=json_graph, gca=gca, gcb=gcb, empty=empty)
        self.connection: connections = connections(json_graph=json_graph)
