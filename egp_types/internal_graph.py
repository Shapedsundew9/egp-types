"""The internal_graph class."""

from __future__ import annotations
from itertools import count
from logging import DEBUG, Logger, NullHandler, getLogger
from pprint import pformat
from random import choice, randint, seed
from typing import Any, Generator, Iterable, Literal, cast
from operator import attrgetter

from .common import random_constant_str
from .egp_typing import (DESTINATION_ROWS, DST_EP, SOURCE_ROWS, SRC_EP,
                         VALID_ROW_SOURCES, DestinationRow, DstEndPointHash,
                         EndPointClass, Row, SourceRow, SrcEndPointHash, EndPointIndex)
from .end_point import (dst_end_point, dst_end_point_ref, isDstEndPoint,
                        isSrcEndPoint, src_end_point, src_end_point_ref,
                        x_end_point)
from .ep_type import EP_TYPE_VALUES_TUPLE, asint
from .graph_validators import igraph_validator

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Compound types
EndPointDict = dict[SrcEndPointHash | DstEndPointHash, x_end_point]
SrcEndPointDict = dict[SrcEndPointHash, src_end_point]
DstEndPointDict = dict[DstEndPointHash, dst_end_point]


class internal_graph(EndPointDict):
    """Convinient structure for GC graph manipulation."""

    def __repr__(self) -> str:
        """Return a mermaid chart flowchart representation of the internal graph.
            flowchart TB
                subgraph R
                    direction TB
                    subgraph Rs
                        direction TB
                        R000s["R000s: ep.typ"]
                        R001s["R000s: ep.typ"]
                        ...
                        Rxxxs["Rxxxs: ep.typ"]
                    end
                    subgraph Rd
                        direction TB
                        R000d["R000d: ep.typ"]
                        R001d["R000d: ep.typ"]
                        ...
                        Rxxxd["Rxxxd: ep.typ"]
                    end
                end
                ...

                x000s --> y004d
                y000s --> z002d
                ...     
        """
        if not self:
            return "Empty internal graph"
        ret_str = "flowchart TB\n"
        for row in sorted(set(ep.row for ep in self.values() if ep.row != "U")):
            ret_str += f"\tsubgraph {row}\n"
            ret_str += "\t\tdirection TB\n"
            if self.num_eps(row, SRC_EP):
                ret_str += f"\t\tsubgraph {row}s\n"
                for ep in self.src_row_filter(row):
                    ret_str += f"\t\t\t{ep.key()}[\"{ep.key()}: {ep.typ}\"]\n"
                ret_str += "\t\tend\n"
            if self.num_eps(row, DST_EP):
                ret_str += f"\t\tsubgraph {row}d\n"
                for ep in self.dst_row_filter(row):
                    ret_str += f"\t\t\t{ep.key()}[\"{ep.key()}: {ep.typ}\"]\n"
                ret_str += "\t\tend\n"
            ret_str += "\tend\n"
        for ep in self.src_filter():
            for ref in ep.refs:
                ret_str += f"\t{ep.key()} --> {ref.key()}\n"
        ret_str += "\n"
        ret_str += "classDef Iclass fill:#999,stroke:#333,stroke-width:4px\n"
        ret_str += "classDef Cclass fill:#444,stroke:#333,stroke-width:4px\n"
        ret_str += "classDef Fclass fill:#0FF,stroke:#333,stroke-width:4px\n"
        ret_str += "classDef Aclass fill:#900,stroke:#333,stroke-width:4px\n"
        ret_str += "classDef Bclass fill:#009,stroke:#333,stroke-width:4px\n"
        ret_str += "classDef Oclass fill:#000,stroke:#333,stroke-width:4px\n"
        ret_str += "classDef Pclass fill:#090,stroke:#333,stroke-width:4px\n"
        ret_str += "\n"
        ret_str += "class I Iclass\n"
        ret_str += "class C Cclass\n"
        ret_str += "class F Fclass\n"
        ret_str += "class A Aclass\n"
        ret_str += "class B Bclass\n"
        ret_str += "class O Oclass\n"
        ret_str += "class P Pclass\n"
        return ret_str
        # return pformat(dict(self), sort_dicts=True, width=180)

    def add(self, ep: x_end_point) -> None:
        """Add an end point to the internal graph."""
        self[ep.key()] = ep

    # TODO: Be clear on rules regarding which methods modify the structure & which return a new structure
    # TODO: Be consistent on whether self modifying method maintains internal consistency
    def json_obj(self) -> dict[str, list[str | int | bool | list[list[str | int]] | None]]:
        """Return a json serializable object."""
        return {ep.key(): ep.json_obj() for ep in self.values()}

    def next_idx(self, row: Row, cls: EndPointClass) -> int:
        """Return the next endpoint index for the class in the row."""
        return len(tuple(self.row_cls_filter(row, cls)))

    def cls_filter(self, cls: EndPointClass) -> Generator[x_end_point, None, None]:
        """Return all the end points in with cls cls."""
        return (ep for ep in self.values() if ep.cls == cls)

    def dst_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points."""
        return (ep for ep in self.values() if isDstEndPoint(ep))

    def src_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points."""
        return (ep for ep in self.values() if isSrcEndPoint(ep))

    def row_filter(self, row: Row) -> Generator[x_end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row)

    def row_cls_filter(self, row: Row, cls: EndPointClass) -> Generator[x_end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row and ep.cls == cls)

    def rows_filter(self, rows: Iterable[Row]) -> Generator[x_end_point, None, None]:
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

    def direct_connect(self, src_row: SourceRow, dst_row: DestinationRow) -> DstEndPointDict:
        """Create a destination row with the exact endpoints needed by src_row."""
        return {n.key(): n for n in (dst_end_point(dst_row, ep.idx, ep.typ) for ep in self.src_row_filter(src_row))}

    def append_connect(self, src_row: SourceRow, dst_row: DestinationRow) -> DstEndPointDict:
        """Create endpoints as they would append to a destination row with the exact endpoints needed by src_row."""
        idx = count(self.next_idx(dst_row, DST_EP))
        return {n.key(): n for n in (dst_end_point(dst_row, next(idx), ep.typ) for ep in self.src_row_filter(src_row))}

    def extend_src(self, src_row: SourceRow, iig: internal_graph) -> None:
        """Extend the source endpoints in src_row by igc row O"""
        idx = count(self.next_idx(src_row, SRC_EP))
        for ep in iig.dst_row_filter("O"):
            self.add(src_end_point(src_row, next(idx), ep.typ))

    def strip_unconnected_dst_eps(self, dst_row: DestinationRow) -> list[EndPointIndex]:
        """Remove all unconnected destination endpoints in dst_row & reindex returning the old indices."""
        for ep in tuple(self.dst_row_filter(dst_row)):
            if not ep.refs:
                del self[ep.key()]
        return self.reindex_dst_row(dst_row)

    def pass_thru(self, dst_row_a: DestinationRow, dst_row_b: DestinationRow, mapping: list[EndPointIndex]) -> SrcEndPointDict:
        """Pass through the endpoints from dst_row_a in RGC to dst_row_b in FGC using mapping."""
        i_eps: Generator[src_end_point, None, None] = (src_end_point("I", ep.idx, ep.typ, refs=[dst_end_point_ref(dst_row_b, mapping.pop(0))]) for ep in self.dst_row_filter(dst_row_a) if ep.refs)
        return {ep.key(): ep for ep in i_eps}

    def row_types(self, row: Row, cls: EndPointClass) -> set[int]:
        """Return the set of types in row."""
        return {ep.typ for ep in self.row_filter(row) if ep.cls == cls}

    def extend_type_interface(self, row: Row) -> None:
        """Extend the internal graph with the types of row."""
        for ep_type in self.row_types(row, DST_EP) - self.row_types("I", SRC_EP):
            self.add(src_end_point("I", self.next_idx("I", SRC_EP), ep_type))
        for ep_type in self.row_types(row, SRC_EP) - self.row_types("O", DST_EP):
            self.add(dst_end_point("O", self.next_idx("O", DST_EP), ep_type))

    def redirect_refs(self, row: Row, cls: EndPointClass, old_ref_row: Row, new_ref_row: Row) -> None:
        """Redirects cls end point references on row from old_ref_row to new_ref_row."""
        for ep in self.row_cls_filter(row, cls):
            ep.redirect_refs(old_ref_row, new_ref_row)

    def as_row(self, row: Literal["A", "B"]) -> EndPointDict:
        """Create a row with the input & output interface of self."""
        io_if: Generator[x_end_point, None, None] = self.rows_filter(("I", "O"))
        return {n.key(): n for n in ((dst_end_point, src_end_point)[not ep.cls](row, ep.idx, ep.typ) for ep in io_if)}

    def complete_references(self) -> None:
        """An incomplete reference is when only one end of the connection references the other."""
        for dst_ep in self.dst_ref_filter():
            cast(src_end_point, self[dst_ep.refs[0].key()]).safe_add_ref(dst_ep.as_ref())
        for src_ep in self.src_ref_filter():
            for src_ref in src_ep.refs:
                cast(dst_end_point, self[src_ref.key()]).safe_add_ref(src_ep.as_ref())

    def remove_all_refs(self) -> None:
        """Remove all references from all endpoints."""
        for ep in self.values():
            ep.refs.clear()

    def remove_row(self, row: Row) -> None:
        """Remove all endpoints in row."""
        for key in tuple(self.keys()):
            if self[key].row == row:
                del self[key]

    def reindex_dst_row(self, row: DestinationRow, clean: bool = False) -> list[EndPointIndex]:
        """Reindex the destination endpoints & correct any uncleaned references retuning the old indices."""
        indices = count()
        retval: list[EndPointIndex] = []
        for ep in sorted(self.dst_row_filter(row), key=attrgetter("idx")):
            old_key: DstEndPointHash = ep.key()
            old_ep_ref: dst_end_point_ref = ep.as_ref()
            retval.append(old_ep_ref.idx)
            ep.idx = next(indices)
            if ep.refs:
                if clean:
                    ep.refs.clear()
                else:
                    other_ep: src_end_point = cast(src_end_point, self[ep.refs[0].key()])
                    # Source endpoints can have multiple references
                    other_ep.refs[other_ep.refs.index(old_ep_ref)].idx = ep.idx
            del self[old_key]
            self[ep.key()] = ep
        return retval

    def reindex_src_row(self, row: SourceRow, clean: bool = False) -> list[EndPointIndex]:
        """Reindex the source endpoints & correct any uncleaned references retuning the old indices."""
        indices = count()
        retval: list[EndPointIndex] = []
        for ep in sorted(self.src_row_filter(row), key=attrgetter("idx")):
            old_key: SrcEndPointHash = ep.key()
            retval.append(ep.idx)
            ep.idx = next(indices)
            if ep.refs:
                if clean:
                    ep.refs.clear()
                else:
                    for ref in ep.refs:
                        other_ep: dst_end_point = cast(dst_end_point, self[ref.key()])
                        # Destination endpoints can only have 1 reference
                        other_ep.refs[0].idx = ep.idx
            del self[old_key]
            self[ep.key()] = ep
        return retval

    def reindex(self, clean: bool = True) -> None:
        """Reindex all endpoints deleting all references by default."""
        if clean:
            self.remove_all_refs()
        counts: dict[str, int] = {}
        for k, ep in sorted(self.items()):
            key: str = ep.row + ("d", "s")[ep.cls]
            ep.idx = counts.setdefault(key, 0)
            counts[key] += 1
            del self[k]
            self[ep.key()] = ep

    def has_row(self, row: Row) -> bool:
        """Return True if the internal graph has the row."""
        return any(ep.row == row for ep in self.values())

    def validate(self) -> bool:
        """Validate the internal graph. This function is not built for speed."""
        validation_structure: dict[str, dict[str, dict[str, list[str | int | bool | list[list[str | int]] | None]]]] = {
            "internal_graph": {k: {k: v} for k, v in self.json_obj().items()}
        }

        # Valid structure and hash keys
        valid: bool = igraph_validator.validate(validation_structure) and all(k == v.key() for k, v in self.items())

        # Valid reference types
        valid = valid and all(isinstance(ep_ref, (src_end_point, dst_end_point)[ep.cls]) for ep in self.values() for ep_ref in ep.refs)

        if not valid and _LOG_DEBUG:
            _logger.debug(f"Validation JSON:\n{pformat(validation_structure, 4)}")
            _logger.debug(f"Internal graph:\n{pformat(self, 4)}")
            _logger.debug(f"Internal graph validation failed:\n{igraph_validator.error_str()}")
        return valid


def internal_graph_from_json(json_igraph: dict[str, list[str | int | bool | list[list[str | int]] | None]]) -> internal_graph:
    """Create an internal graph from a json object."""
    if _LOG_DEBUG:
        for k, v in json_igraph.items():
            assert k[0] == v[0], f"Key {k} first character does not match record row {v[0]}"
            assert int(k[1:4]) == v[1], f"Key {k} index does not match record index {v[1]}"
            assert k[4] == ("d", "s")[cast(int, v[3])], f"Key {k} class does not match record class {v[3]}"
    json_igraph_lists: list[list[Any]] = [
        [*v[:4], [(src_end_point_ref, dst_end_point_ref)[cast(int, v[3])](*r) for r in cast(list, v[4])], v[5]]
        for v in json_igraph.values()
    ]
    json_igraph_eps: list[x_end_point] = [dst_end_point(*ep_list) for ep_list in json_igraph_lists if ep_list[3] == DST_EP]
    json_igraph_eps.extend([src_end_point(*ep_list) for ep_list in json_igraph_lists if ep_list[3] == SRC_EP])
    return internal_graph({ep.key(): ep for ep in json_igraph_eps})


def random_internal_graph(
    rows: str,
    ep_types: tuple[int, ...] = tuple(),
    max_row_eps: int = 8,
    verify: bool = False,
    rseed: int | None = None,
    row_stablization: bool = False,
) -> internal_graph:
    """Random internal graph generator.

    All rows specified will have at least one endpoint. The number of endpoints or each class per row is randomly generated
    between 1 and max_row_eps. The endpoint types are randomly selected from ep_types. If ep_types is not specified.

    Row stabilization ensures that the graph has no rows with destinations that cannot be reached from a source.
    This is not full stabilization as a source row may be available but not have the correct endpoint types. This
    can be mitigated by defining only one type.
    """
    has_f: bool = "F" in rows
    has_o: bool = "O" in rows
    igraph: internal_graph = internal_graph()

    # Set defaults
    if not ep_types:
        ep_types = EP_TYPE_VALUES_TUPLE[2:]
    if seed is not None:
        seed(rseed)

    if _LOG_DEBUG:
        _logger.debug(
            f"rows: {rows}, ep_types: {ep_types}, max_row_eps: {max_row_eps}, verify: {verify}, rseed: {rseed}, row_stablization: {row_stablization}"
        )

    # For each row to be generated add them to the internal graph
    for row in rows.replace("P", ""):
        # Row F is a bit special
        if row == "F":
            igraph.add(src_end_point("I", 0, asint("bool")))
            igraph.add(dst_end_point("F", 0, asint("bool")))
        # For destinations rows make sure there is a valid source row to reference
        elif row_stablization and (row in DESTINATION_ROWS and any(vsr in VALID_ROW_SOURCES[has_f][row] for vsr in rows)):
            for idx in range(randint(1, max_row_eps)):
                igraph.add(dst_end_point(row, idx, choice(ep_types)))
        if row in SOURCE_ROWS:
            for idx in range(randint(1, max_row_eps)):
                igraph.add(src_end_point(row, idx, choice(ep_types)))

    # Only corner is if there is a row F or P
    if has_f and has_o:
        igraph.update(igraph.move_row("O", "P", True))

    # Make sure all the constant strings are valid
    for const_ep in igraph.row_filter("C"):
        const_ep.val = random_constant_str(const_ep.typ)

    # No references to clean out.
    igraph.reindex(False)
    if _LOG_DEBUG:
        _logger.debug(f"Random internal graph post-refactor:\n{pformat(igraph, 4, width=180)}")

    # Validate the internal graph
    if verify and not igraph.validate():
        _logger.debug(f"Validator error:\n{igraph_validator.error_str()}")
        raise ValueError(f"Invalid random internal graph:\n{pformat(igraph, 4, width=180)}")
    return igraph
