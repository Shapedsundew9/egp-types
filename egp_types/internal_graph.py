"""The internal_graph class."""

from __future__ import annotations
from itertools import count
from logging import DEBUG, Logger, NullHandler, getLogger
from pprint import pformat
from random import choice, randint, seed
from typing import Any, Generator, Iterable, Literal, cast
from operator import attrgetter

from .common import random_constant_str
from .egp_typing import (
    DESTINATION_ROWS,
    DST_EP,
    SOURCE_ROWS,
    SRC_EP,
    ROWS,
    VALID_ROW_SOURCES,
    DestinationRow,
    DstEndPointHash,
    EndPointClass,
    Row,
    SourceRow,
    SrcEndPointHash,
    EndPointIndex,
    EndPointType,
    JSONGraph,
    CVI,
    CPI,
    PairIdx,
    isDestinationRow,
)
from .end_point import dst_end_point, dst_end_point_ref, isDstEndPoint, isSrcEndPoint, src_end_point, src_end_point_ref, x_end_point
from .ep_type import EP_TYPE_VALUES_TUPLE, asint
from .graph_validators import igraph_validator
from .mermaid_charts import MERMAID_IGRAPH_CLASS_DEF_STR, MERMAID_IGRAPH_COLORS


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Compound types
EndPointDict = dict[SrcEndPointHash | DstEndPointHash, x_end_point]
SrcEndPointDict = dict[SrcEndPointHash, src_end_point]
DstEndPointDict = dict[DstEndPointHash, dst_end_point]


# Mermaid chart formatting.
# Can be pasted after the flowchart definition of the internal chart to add colouring/formatting etc.
MERMAID_IGRAPH_CLASS_STR = (
    "\n"
    "class I0000 Iclass\n"
    "class C0000 Cclass\n"
    "class F0000 Fclass\n"
    "class A0000 Aclass\n"
    "class B0000 Bclass\n"
    "class O0000 Oclass\n"
    "class P0000 Pclass\n"
)
MERMAID_IGRAPH_FORMAT_STR: str = "\n".join(MERMAID_IGRAPH_CLASS_DEF_STR) + MERMAID_IGRAPH_CLASS_STR
_logger.debug(f"Mermaid chart formatting for internal graph representation:\n{MERMAID_IGRAPH_FORMAT_STR}\n")


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
            return "\n%% Instance ID: {id(self)}\nEmpty internal graph\n"
        ret_list_str: list[str] = [f"\n%% Paste into https://mermaid.live/\n%% Instance ID: {id(self)}\nflowchart TB\n"]
        ret_list_str.extend(self.mermaid_subgraph_str())
        ret_list_str.append("\n")
        ret_list_str.extend(self.mermaid_link_str())
        return "\n".join(ret_list_str)

    def add(self, ep: x_end_point) -> None:
        """Add an end point to the internal graph."""
        self[ep.key()] = ep

    def append_connect(self, src_row: SourceRow, dst_row: DestinationRow) -> DstEndPointDict:
        """Create endpoints as they would append to a destination row with the exact endpoints needed by src_row."""
        idx = count(self.next_idx(dst_row, DST_EP))
        return {n.key(): n for n in (dst_end_point(dst_row, next(idx), ep.typ) for ep in self.src_row_filter(src_row))}

    def cls_filter(self, cls: EndPointClass) -> Generator[x_end_point, None, None]:
        """Return all the end points in with cls cls."""
        return (ep for ep in self.values() if ep.cls == cls)

    def complete_dst_references(self, row: DestinationRow) -> None:
        """An incomplete reference is when only one end of the connection references the other."""
        for dst_ep in self.dst_row_filter(row):
            cast(src_end_point, self[dst_ep.refs[0].key()]).refs.append(dst_ep.as_ref())

    def complete_src_references(self, row: SourceRow) -> None:
        """An incomplete reference is when only one end of the connection references the other."""
        for src_ep in self.src_row_filter(row):
            for src_ref in src_ep.refs:
                cast(dst_end_point, self[src_ref.key()]).refs.append(src_ep.as_ref())

    def copy_row(self, row: Row, clean: bool = False) -> EndPointDict:
        """Return a copy of the specified row endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if ep.row == row}

    def copy_rows(self, rows: Iterable[Row], clean: bool = False) -> EndPointDict:
        """Return a copy of the specified rows endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if ep.row in rows}

    def copy_rows_dst_eps(self, rows: Iterable[Row], clean: bool = False) -> DstEndPointDict:
        """Return a copy of the specified rows destination endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if isDstEndPoint(ep) and ep.row in rows}

    def copy_rows_src_eps(self, rows: Iterable[Row], clean: bool = False) -> SrcEndPointDict:
        """Return a copy of the specified rows source endpoints. Remove references if clean is True."""
        return {key: ep.copy(clean) for key, ep in self.items() if isSrcEndPoint(ep) and ep.row in rows}

    def direct_connect(self, src_row: SourceRow, dst_row: DestinationRow) -> DstEndPointDict:
        """Create a destination row with the exact endpoints needed by src_row."""
        return {n.key(): n for n in (dst_end_point(dst_row, ep.idx, ep.typ, refs=[ep.as_ref()]) for ep in self.src_row_filter(src_row))}

    def dst_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points."""
        return (ep for ep in self.values() if isDstEndPoint(ep))

    def dst_ref_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points that are referenced."""
        return (ep for ep in self.values() if ep.row != "U" and ep.refs and isDstEndPoint(ep))

    def dst_row_filter(self, row: Row) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points in a row."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row == row)

    def dst_rows_filter(self, rows: Iterable[DestinationRow]) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points in the specified rows."""
        return (ep for ep in self.values() if isDstEndPoint(ep) and ep.row in rows)

    def dst_unref_filter(self) -> Generator[dst_end_point, None, None]:
        """Return all the destination end points that are unreferenced."""
        return (ep for ep in self.values() if not ep.refs and ep.row != "U" and isDstEndPoint(ep))

    def extend_src(self, src_row: SourceRow, iig: internal_graph) -> None:
        """Extend the source endpoints in src_row by igc row O"""
        idx = count(self.next_idx(src_row, SRC_EP))
        for ep in iig.dst_row_filter("O"):
            self.add(src_end_point(src_row, next(idx), ep.typ))

    def extend_type_interface(self, row: Row) -> None:
        """Extend the internal graph with the types of row."""
        for ep_type in self.row_types(row, DST_EP) - self.row_types("I", SRC_EP):
            self.add(src_end_point("I", self.next_idx("I", SRC_EP), ep_type))
        for ep_type in self.row_types(row, SRC_EP) - self.row_types("O", DST_EP):
            self.add(dst_end_point("O", self.next_idx("O", DST_EP), ep_type))

    def has_row(self, row: Row) -> bool:
        """Return True if the internal graph has the row."""
        return any(ep.row == row for ep in self.values())

    # TODO: Be clear on rules regarding which methods modify the structure & which return a new structure
    # TODO: Be consistent on whether self modifying method maintains internal consistency
    def json_obj(self) -> dict[str, list[str | int | bool | list[list[str | int]] | None]]:
        """Return a json serializable object."""
        return {ep.key(): ep.json_obj() for ep in self.values()}

    def json_graph(self) -> JSONGraph:
        """Convert internal graph to JSON graph."""
        jgraph: JSONGraph = {}
        for ep in sorted(self.dst_filter(), key=lambda x: x.idx):
            row: DestinationRow = ep.row
            jgraph.setdefault(row, []).append([ep.refs[0].row, ep.refs[0].idx, ep.typ])
        for ep in sorted(self.row_filter("C"), key=lambda x: x.idx):
            if "C" not in jgraph:
                jgraph["C"] = []
            jgraph.setdefault("C", []).append([ep.val, ep.typ])
        return jgraph

    def mermaid_class_str(self, uid: int = 0) -> list[str]:
        """Return the mermaid class style lists."""
        return [f"class {r}{uid:04x} {r}class" for r in ROWS]

    def mermaid_embedded_str(self, uid: int = 0) -> tuple[list[str], list[str]]:
        """Return the mermaid chart representation of the internal graph."""
        ret_list_str: list[str] = self.mermaid_subgraph_str(uid)
        link_list_str: list[str] = self.mermaid_link_str(uid)
        return ret_list_str, link_list_str

    def mermaid_link_str(self, uid: int = 0) -> list[str]:
        """Return the mermaid chart link representation of the internal graph."""
        ret_list_str: list[str] = []
        for ep in self.src_filter():
            for ref in ep.refs:
                ret_list_str.append(f"\t{ep.key()}{uid:04x} --> {ref.key()}{uid:04x}")
        return ret_list_str

    def mermaid_style_str(self, link_list_str: list[str]) -> list[str]:
        """Return the mermaid link style lists."""
        row_link_counts: dict[Row, list[str]] = {r: [] for r in ROWS}
        for i, link_str in enumerate(link_list_str):
            row_link_counts[cast(Row, link_str[1])].append(str(i))
        return [
            f"linkStyle {','.join(link_counts)} stroke:{MERMAID_IGRAPH_COLORS[row]['link']}"
            for row, link_counts in row_link_counts.items()
            if link_counts
        ]

    def mermaid_subgraph_str(self, uid: int = 0) -> list[str]:
        """Return the mermaid chart subgraph representation of the internal graph."""
        # Add the relevant row subgraphs
        ret_list_str: list[str] = []
        for row in sorted(set(ep.row for ep in self.values() if ep.row != "U")):
            ret_list_str.append(f'\tsubgraph {row}{uid:04x}["{row}"]')
            ret_list_str.append("\t\tdirection TB")
            if self.num_eps(row, SRC_EP):
                ret_list_str.append(f'\t\tsubgraph {row}s{uid:04x}["{row}s"]')
                for ep in self.src_row_filter(row):
                    ret_list_str.append(f'\t\t\t{ep.key()}{uid:04x}["{ep.key()}: {ep.typ}"]')
                ret_list_str.append("\t\tend")
            if self.num_eps(row, DST_EP):
                ret_list_str.append(f'\t\tsubgraph {row}d{uid:04x}["{row}d"]')
                for ep in self.dst_row_filter(row):
                    ret_list_str.append(f'\t\t\t{ep.key()}{uid:04x}["{ep.key()}: {ep.typ}"]')
                ret_list_str.append("\t\tend")
            ret_list_str.append("\tend")
        return ret_list_str

    def move_row(self, f_row: Row, t_row: Row, clean: bool = False, has_f: bool = False) -> EndPointDict:
        """Return a copy of the specified f_row endpoints mapped to t_row. Remove references if clean is True."""
        return {n.key(): n for n in (ep.move_copy(t_row, clean, has_f) for ep in self.values() if ep.row == f_row)}

    def next_idx(self, row: Row, cls: EndPointClass) -> int:
        """Return the next endpoint index for the class in the row."""
        return len(tuple(self.row_cls_filter(row, cls)))

    def num_eps(self, row: Row, cls: EndPointClass) -> int:
        """Count the endpoint of class cls in a specific row."""
        return sum(ep.cls == cls and ep.row == row for ep in self.values())

    def pass_thru(self, dst_row_a: DestinationRow, dst_row_b: DestinationRow, mapping: list[EndPointIndex]) -> SrcEndPointDict:
        """Pass through the endpoints from dst_row_a in RGC to dst_row_b in FGC using mapping."""
        i_eps: Generator[src_end_point, None, None] = (
            src_end_point("I", ep.idx, ep.typ, refs=[dst_end_point_ref(dst_row_b, mapping.pop(0))])
            for ep in self.dst_row_filter(dst_row_a)
            if ep.refs
        )
        return {ep.key(): ep for ep in i_eps}

    def redirect_refs(self, row: Row, cls: EndPointClass, old_ref_row: Row, new_ref_row: Row) -> None:
        """Redirects cls end point references on row from old_ref_row to new_ref_row.
        Does not modifiy old_ref or new_ref endpoints. These endpoints must be change separately to maintain consistency.
        """
        for ep in self.row_cls_filter(row, cls):
            ep.redirect_refs(old_ref_row, new_ref_row)

    def as_row(self, row: Literal["A", "B"]) -> EndPointDict:
        """Create a row with the input & output interface of self."""
        io_if: Generator[x_end_point, None, None] = self.rows_filter(("I", "O"))
        return {n.key(): n for n in ((dst_end_point, src_end_point)[not ep.cls](row, ep.idx, ep.typ) for ep in io_if)}

    def remove_all_refs(self) -> None:
        """Remove all references from all endpoints."""
        for ep in self.values():
            ep.refs.clear()

    def remove_row(self, row: Row) -> None:
        """Remove all endpoints in row."""
        for key in tuple(self.keys()):
            if self[key].row == row:
                del self[key]

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

    def row_cls_filter(self, row: Row, cls: EndPointClass) -> Generator[x_end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row and ep.cls == cls)

    def row_filter(self, row: Row) -> Generator[x_end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row == row)

    def rows_filter(self, rows: Iterable[Row]) -> Generator[x_end_point, None, None]:
        """Return all the end points in row."""
        return (ep for ep in self.values() if ep.row in rows)

    def row_types(self, row: Row, cls: EndPointClass) -> set[int]:
        """Return the set of types in row."""
        return {ep.typ for ep in self.row_filter(row) if ep.cls == cls}

    def src_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points."""
        return (ep for ep in self.values() if isSrcEndPoint(ep))

    def src_ref_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points that are referenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.refs)

    def src_row_filter(self, row: Row) -> Generator[src_end_point, None, None]:
        """Return all the source end points in a row."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row == row)

    def src_rows_filter(self, rows: Iterable[SourceRow]) -> Generator[src_end_point, None, None]:
        """Return all the source end points in the specified rows."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and ep.row in rows)

    def src_unref_filter(self) -> Generator[src_end_point, None, None]:
        """Return all the source end points that are unreferenced."""
        return (ep for ep in self.values() if isSrcEndPoint(ep) and not ep.refs)

    def strip_unconnected_dst_eps(self, dst_row: DestinationRow) -> list[EndPointIndex]:
        """Remove all unconnected destination endpoints in dst_row & reindex returning the old indices."""
        for ep in tuple(self.dst_row_filter(dst_row)):
            if not ep.refs:
                del self[ep.key()]
        return self.reindex_dst_row(dst_row)

    def validate(self) -> bool:
        """Validate the internal graph. This function is not built for speed."""
        validation_structure: dict[str, dict[str, dict[str, list[str | int | bool | list[list[str | int]] | None]]]] = {
            "internal_graph": {k: {k: v} for k, v in self.json_obj().items()}
        }

        # Valid structure and hash keys
        valid: bool = igraph_validator.validate(validation_structure) and all(k == v.key() for k, v in self.items())
        if not valid:
            _logger.debug("igraph_validator returned False.")

        # Valid reference types
        valid = valid and all(
            isinstance(ep_ref, (src_end_point_ref, dst_end_point_ref)[ep.cls]) for ep in self.values() for ep_ref in ep.refs
        )

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


def internal_graph_from_JSONGraph(json_graph: JSONGraph) -> internal_graph:
    """Convert JSON graph to internal format.

    The internal format allows quicker searching for parameters by type, endpoint type etc.
    It maintains bi-directional references for quick manipulation.
    Types are stored in integer format for efficiency.
    """
    i_graph: internal_graph = internal_graph()

    # Row C needs to be imported before any other row to ensure references exist.
    for index, c_point in enumerate(json_graph.get("C", [])):
        src_ep: x_end_point = src_end_point("C", index, cast(EndPointType, c_point[CVI.TYP.value]), refs=[], val=c_point[CVI.VAL.value])
        i_graph[src_ep.key()] = src_ep

    for jgraph_pair in json_graph.items():
        if isDestinationRow(jgraph_pair[PairIdx.ROW.value]):
            row: DestinationRow = cast(DestinationRow, jgraph_pair[PairIdx.ROW.value])
            for index, c_point in enumerate(jgraph_pair[PairIdx.VALUES.value]):
                cp_row: SourceRow = cast(SourceRow, c_point[CPI.ROW.value])
                cp_idx: EndPointIndex = cast(EndPointIndex, c_point[CPI.IDX.value])
                cp_typ: EndPointType = cast(EndPointType, c_point[CPI.TYP.value])
                dst_ep: dst_end_point = dst_end_point(row, index, cp_typ, refs=[src_end_point_ref(cp_row, cp_idx)])
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to i_graph: {dst_ep}")
                i_graph[dst_ep.key()] = dst_ep
                src_ep_hash: SrcEndPointHash = dst_ep.refs[0].key()
                if src_ep_hash in i_graph and row != "U":
                    cast(src_end_point, i_graph[src_ep_hash]).refs.append(dst_end_point_ref(row, index))
                elif cp_row != "C":
                    refs: list[dst_end_point_ref] = [dst_end_point_ref(row, index)] if row != "U" else []
                    i_graph[src_ep_hash] = src_end_point(cp_row, cp_idx, cp_typ, refs=refs)
                    if _LOG_DEBUG:
                        _logger.debug(f"Adding to i_graph: {i_graph[src_ep_hash]}")
    return i_graph


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
    if rseed is not None:
        seed(rseed)

    if _LOG_DEBUG:
        _logger.debug(
            f"rows: {rows}, ep_types: {ep_types}, max_row_eps: {max_row_eps}, verify: "
            f"{verify}, rseed: {rseed}, row_stablization: {row_stablization}"
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
