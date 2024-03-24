"""Tools for managing genetic code graphs.

Created Date: Sunday, July 19th 2020, 2:56:11 pm
Author: Shapedsundew9

Description: Genetic code graphs define how genetic codes are connected together. The gc_graph_tools module
defines the rules of the connectivity (the "physics") i.e. what is possible to observe or occur.
"""

from collections import Counter
from copy import deepcopy
from itertools import count
from logging import DEBUG, Logger, NullHandler, getLogger
from random import choice, randint, sample
from typing import Iterable, Sequence, cast

from egp_utils.base_validator import base_validator
from surebrec.surebrec import generate
from text_token import register_token_code, text_token

from .common import random_constant_str
from .egp_typing import (
    DST_EP,
    ROWS,
    SOURCE_ROWS,
    SRC_EP,
    VALID_ROW_DESTINATIONS,
    VALID_ROW_SOURCES,
    DestinationRow,
    EndPointClass,
    EndPointHash,
    JSONGraph,
    Row,
    SourceRow,
)
from .end_point import dst_end_point, dst_end_point_ref, end_point_ref, src_end_point, src_end_point_ref, x_end_point
from .ep_type import REAL_EP_TYPE_VALUES, asint, asstr, compatible, validate, validate_value
from .internal_graph import internal_graph, internal_graph_from_JSONGraph

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


register_token_code("E01000", "A graph must have at least one output.")
register_token_code("E01001", "{ep_hash} endpoint is not connected to anything.")
register_token_code("E01002", "{ep_hash} endpoint does not have a valid type: {type_errors}")
register_token_code(
    "E01003",
    "{cls_str} row {row} does not have contiguous indices starting at 0: {indices}.",
)
register_token_code(
    "E01004",
    "The {cls_str} row {row} endpoint count ({row_count}) != i_graph count ({i_count})",
)
register_token_code("E01005", "Constant {ref} does not have a valid value ({value}) for type {type}.")
register_token_code("E01006", 'If row "P" is defined then row "F" must be defined.')
register_token_code("E01007", "Endpoint {ref} must be a source.")
register_token_code("E01008", "Endpoint {ref} must be a destination.")
register_token_code(
    "E01009",
    "Source endpoint {ref1} type {type1} is not compatible with destination endpoint {ref2} type {type2}.",
)
register_token_code(
    "E01010",
    "Destination endpoint {ref1} cannot be connected to source endpoint {ref2}.",
)
register_token_code(
    "E01011",
    'Destination endpoint {ref1} cannot be connected to source endpoint {ref2} when row "F" exists.',
)
register_token_code("E01012", 'Endpoint {ref1} cannot reference row B {ref2} if "F" is defined.')
register_token_code(
    "E01013",
    'Row "P" length ({len_p}) must be the same as row "O" length ({len_o}) when "F" is defined.',
)
register_token_code("E01014", 'Row "U" endpoint {u_ep} referenced by more than one endpoint {refs}.')
register_token_code(
    "E01015",
    'Row "U" endpoint {u_ep} references a constant that does not exist {refs}.',
)
register_token_code(
    "E01016",
    'Row "I" must contain at least one bool type source endpoint if "F" is defined.',
)
register_token_code(
    "E01017",
    "Source endpoint {ref1} cannot be connected to destination endpoint {ref2}.",
)
register_token_code("E01018", "Destination endpoint {dupe} is connected to multiple sources {refs}.")
register_token_code("E01019", "Endpoint {ep_hash} references {ref_hash} but it does not exist.")
register_token_code(
    "E01020",
    "Endpoint {ep_hash} references {ref_hash} but {ref_hash} does not reference it back.",
)
register_token_code(
    "E01021",
    'Source row endpoint {ep_hash} has no references but is not referenced by row "U".',
)
register_token_code(
    "E01022",
    'Row "U" endpoint {ep_hash} references a source that does not exist or is connected.',
)
register_token_code(
    "E01023",
    'Row "P" endpoint {p_hash} is not the same type as row "O" {o_hash} and is required to be.',
)
register_token_code(
    "E01024",
    'Row "F" must have 1 and only 1 destination endpoint.',
)
register_token_code(
    "E01025",
    'Row "F" must have no source endpoints.',
)
register_token_code(
    "E01026",
    'Row "F"s single destination endpoint must be of type bool.',
)
register_token_code(
    "E01027",
    'Row "U" cannot have any sources.',
)
register_token_code(
    "E01028",
    "Internal graph failed validation.",
)
register_token_code(
    "E01029",
    "Endpoint {ep} contains duplicate references.",
)

register_token_code("I01000", '"I" row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01001", '"I" row endpoint removed.')
register_token_code("I01002", "Source row endpoint {ep_hash} has no references.")
register_token_code("I01100", '"A" source row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01101", '"A" source row endpoint removed.')
register_token_code("I01102", '"A" destination row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01103", '"A" destination row endpoint removed.')
register_token_code("I01200", '"B" source row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01201", '"B" source row endpoint removed.')
register_token_code("I01202", '"B" destination row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01203", '"B" destination row endpoint removed.')
register_token_code("I01302", '"O" row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01303", '"O" row endpoint removed.')
register_token_code("I01402", '"P" row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code("I01403", '"P" row endpoint removed.')

register_token_code("I01900", "No source endpoints in the list to remove.")


# TODO: Consider caching calculated results.
class gc_graph:
    """Manipulating Genetic Code Graphs."""

    def __init__(self, json_graph: JSONGraph) -> None:
        self.igraph: internal_graph = internal_graph_from_JSONGraph(json_graph)
        self.status = []
        self.rows: tuple[dict[Row, int], dict[Row, int]] = (
            dict(Counter([ep.row for ep in self.igraph.dst_filter()])),
            dict(Counter([ep.row for ep in self.igraph.src_filter()])),
        )

    def __repr__(self) -> str:
        """Return a string representation of the graph."""
        return self.igraph.__repr__()

    def _add_ep(self, ep: x_end_point) -> None:
        """Add an endpoint to the internal graph format structure.

        Other than _convert_to_internal() this MUST be the only way to add end points.
        """
        row_counts: dict[Row, int] = self.rows[ep.cls]
        if ep.row not in self.rows[ep.cls]:
            row_counts[ep.row] = 0
        ep.idx = row_counts[ep.row]
        self.igraph[ep.key()] = ep
        row_counts[ep.row] += 1

    def _remove_ep(self, ep: x_end_point, check: bool = True) -> None:
        """Remove an endpoint to the internal graph format structure.

        Other than _convert_to_internal() this MUST be the only way to remove end points.

        Args
        ----
            ep: An endpoint list structure to be removed from the internal graph.
            check: Only remove end point if it is unreferenced when true.
        """
        if not check or not ep.refs:
            del self.igraph[ep.key()]
            self.rows[ep.cls][ep.row] -= 1
            if not self.rows[ep.cls][ep.row] and not self.rows[not ep.cls].get(ep.row, 0):
                del self.rows[ep.cls][ep.row]

    def has_row(self, row: Row) -> bool:
        """Return True if the row exists in the graph."""
        return row in self.rows[SRC_EP] or row in self.rows[DST_EP]

    def add_input(self, ep_type: int | None = None) -> None:
        """Create and append an unconnected row I endpoint.

        Args
        ----
        ep_type: ep_type in integer format. If None a random real ep_type is chosen.
        """
        if ep_type is None:
            self._add_ep(src_end_point("I", self.rows[SRC_EP].get("I", 0), choice(REAL_EP_TYPE_VALUES)))
        else:
            self._add_ep(src_end_point("I", self.rows[SRC_EP].get("I", 0), ep_type))

    def remove_input(self, idx: int | None = None) -> None:
        """Remove input idx.

        No-op if there are no inputs.

        Args
        ----
        idx: Index of input to remove. If None a random index is chosen.
        """
        num_inputs: int = self.rows[SRC_EP].get("I", 0)
        if num_inputs:
            nidx: int = randint(0, num_inputs - 1) if idx is None else idx
            ep_ref: src_end_point_ref = src_end_point_ref("I", nidx)
            if _LOG_DEBUG:
                _logger.debug(f"Removing input {ep_ref}.")
            ep: src_end_point = cast(src_end_point, self.igraph[ep_ref.key()])
            self._remove_ep(ep, False)
            for ref in ep.refs:
                cast(dst_end_point, self.igraph[ref.key()]).refs.remove(ep_ref)

            # Only re-index row I if it was not the last endpoint that was removed (optimisation)
            if nidx != num_inputs - 1:
                self.reindex_row("I")

    def add_output(self, ep_type: int | None = None) -> None:
        """Create and append an unconnected row O endpoint.

        Args
        ----
        ep_type: ep_type in integer format. If None a random real ep_type is chosen.
        """
        if ep_type is None:
            graph_viable_types = tuple(self.viable_dst_types("O"))
            nep_type: int = choice(graph_viable_types) if graph_viable_types else choice(REAL_EP_TYPE_VALUES)
        else:
            nep_type = ep_type
        o_index: int = self.rows[DST_EP].get("O", 0)
        self._add_ep(dst_end_point("O", o_index, nep_type))
        if self.has_row("F"):
            self._add_ep(dst_end_point("P", o_index, nep_type))

    def remove_output(self, idx: int | None = None) -> None:
        """Remove output idx.

        No-op if there are no outputs.

        Args
        ----
        idx: Index of output to remove. If None a random index is chosen.
        """
        num_outputs: int = self.rows[DST_EP].get("O", 0)
        if num_outputs:
            nidx: int = randint(0, num_outputs - 1) if idx is None else idx
            ep_ref: dst_end_point_ref = dst_end_point_ref("O", nidx)
            if _LOG_DEBUG:
                _logger.debug(f"Removing output {ep_ref}.")
            # We know from the ep_ref type which endpoint type will be returned
            ep: dst_end_point = cast(dst_end_point, self.igraph[ep_ref.key()])
            self._remove_ep(ep, False)
            for ref in ep.refs:
                cast(src_end_point, self.igraph[ref.key()]).refs.remove(ep_ref)

            # If F exists then must deal with P
            if self.has_row("F"):
                ep_ref: dst_end_point_ref = dst_end_point_ref("P", nidx)
                if _LOG_DEBUG:
                    _logger.debug(f"Removing output {ep_ref}.")
                ep: dst_end_point = cast(dst_end_point, self.igraph[ep_ref.key()])
                self._remove_ep(ep, False)
                for ref in ep.refs:
                    cast(src_end_point, self.igraph[ref.key()]).refs.remove(ep_ref)

            # Only re-index row O if it was not the last endpoint that was removed (optimisation)
            if idx != num_outputs - 1:
                self.reindex_row("O")
                if self.has_row("F"):
                    self.reindex_row("P")

    def remove_constant(self, idx=None) -> None:
        """Remove constant idx.

        No-op if there are no constants.

        Args
        ----
        idx: Index of constant to remove. If None a random index is chosen.
        """
        num_constants: int = self.rows[SRC_EP].get("C", 0)
        if num_constants:
            nidx: int = randint(0, num_constants - 1) if idx is None else idx
            ep_ref: src_end_point_ref = src_end_point_ref("C", nidx)
            if _LOG_DEBUG:
                _logger.debug(f"Removing constant {ep_ref}.")
            ep: src_end_point = cast(src_end_point, self.igraph[ep_ref.key()])
            self._remove_ep(ep, False)
            for ref in ep.refs:
                cast(dst_end_point, self.igraph[ref.key()]).refs.remove(ep_ref)

            # Only re-index row I if it was not the last endpoint that was removed (optimisation)
            if nidx != num_constants - 1:
                self.reindex_row("C")

    def add_inputs(self, inputs: Iterable[int]) -> None:
        """Create and add unconnected row I endpoints.

        Will replace any existing endpoints with the same index.

        Args
        ----
        inputs: ep_types in integer format.
        """
        for index, i in enumerate(inputs):
            self._add_ep(src_end_point("I", index, i))

    def add_outputs(self, outputs: Iterable[int]) -> None:
        """Create and add unconnected row O endpoints.

        Will replace any existing endpoints with the same index.

        Args
        ----
        outputs: ep_types in integer format.
        """
        for index, i in enumerate(outputs):
            self._add_ep(dst_end_point("O", index, i))

    def _num_eps(self, row: Row, ep_cls: EndPointClass) -> int:
        """Return the number of ep_type endpoints in row.

        If the effective logger level is DEBUG then a self consistency check is done.

        Args
        ----
        row: One of gc_graph.rows.
        ep_cls: DST_EP or SRC_EP

        Returns
        -------
        Count of the specified endpoints.
        """
        return self.rows[ep_cls].get(row, 0)

    def reindex_row(self, row: Row, cls: EndPointClass | None = None) -> None:
        """Re-index row.

        If end points have been removed from a row the row will need
        reindexing so the indicies are contiguous (starting at 0).

        Rows A & B cannot be reindexed in normal operation as their interfaces are bound to
        a GC definition.

        All rows are supported for re-indexing to generate test cases.

        Args
        ----
        row: Any valid row letter.
        cls: Source or destination endpoints or None
        """
        # Its necessary to sort the indices so we do not map an index twice.
        if cls is None:
            eps: list[x_end_point] = sorted(self.igraph.row_filter(row), key=lambda x: x.idx)
        elif cls == DST_EP:
            eps = sorted(self.igraph.dst_row_filter(row), key=lambda x: x.idx)
        else:
            eps = sorted(self.igraph.src_row_filter(row), key=lambda x: x.idx)

        if eps:
            # Map the indices to a contiguous integer sequence starting at 0
            r_map: dict[int, int] = {idx: i for i, idx in enumerate((ep.idx for ep in eps))}
            # For each row select all the endpoints and iterate through the references to them
            # For each reference update: Find the reverse reference and update it with the new index
            # Finally update the index in the endpoint
            if _LOG_DEBUG:
                _logger.debug(f"Reindexing row {row} {('DST', 'SRC')[cls] if cls is not None else 'ALL'} endpoints.")
            for ep in eps:
                if r_map[ep.idx] != ep.idx:
                    if _LOG_DEBUG:
                        _logger.debug(f"Mapping {ep.key()} to {end_point_ref(ep.row, r_map[ep.idx]).force_key(ep.cls)}")
                        _logger.debug(f"References to re-index: {ep.refs}")
                    for ref in ep.refs:
                        for refd in self.igraph[ref.force_key(not ep.cls)].refs:
                            if refd.row == row and refd.idx == ep.idx:
                                refd.idx = r_map[ep.idx]
                    del self.igraph[ep.key()]
                    ep.idx = r_map[ep.idx]
                    self.igraph[ep.key()] = ep

    def reindex(self) -> None:
        """Reindex all rows."""
        for row in self.rows[DST_EP]:
            self.reindex_row(row, DST_EP)
        for row in self.rows[SRC_EP]:
            self.reindex_row(row, SRC_EP)

    def purge_unconnectable_types(self) -> None:
        """This is a test case function.

        Remove any destination endpoints that do not have compatible source endpoints.
        This is not a useful function in normal operation.
        """
        for row in deepcopy(self.rows[DST_EP]):  # self.rows may be modified during iteration
            src_types: set[int] = {ep.typ for ep in self.igraph.src_rows_filter(VALID_ROW_SOURCES[self.has_row("F")][row])}
            dst_types: set[int] = {ep.typ for ep in self.igraph.dst_row_filter(row)}
            unconnectable_types: set[int] = dst_types - src_types
            if _LOG_DEBUG:
                _logger.debug(f"Unconnectable types for row {row}: {unconnectable_types}")
            for unconnectable_type in unconnectable_types:
                for ep in filter(
                    lambda x, uct=unconnectable_type: x.typ == uct,
                    tuple(self.igraph.dst_row_filter(row)),
                ):
                    self._remove_ep(ep)

    def normalize(self) -> bool:
        """Make the graph consistent.

        The make the graph consistent the following operations are performed:
            1. Clean row U.
            2. Connect all unconnected destinations to existing sources if possible
            3. Reference all unconnected sources in row 'U'
            4. Check a valid steady state has been achieved
            5. self.app_graph is regenerated
        """
        # TODO: Need to put in a check for normalizing a graph that has not been modified since last normalization.
        _logger.debug("Normalising...")

        # 1. Remove all references to U before starting
        for ep in tuple(self.igraph.row_filter("U")):
            # TODO: Can we do this quicker. Do not need to check references?
            self._remove_ep(ep, check=False)

        # There should be no references to 'U'
        # for ep in self.i_graph.values():
        #     victims = reversed(tuple(idx for idx, ref in enumerate(ep.refs) if ref.row == 'U'))
        #     for idx in victims:
        #         del ep.refs[idx]

        # 2 Connect all destinations to existing sources if possible
        self.connect_all()

        # 3 Reference all unconnected sources in row 'U'
        for idx, ep in enumerate(tuple(self.igraph.src_unref_filter())):
            self._add_ep(dst_end_point("U", idx, ep.typ, refs=[src_end_point_ref(ep.row, ep.idx)]))

        # 4 Check a valid steady state has been achieved
        # 5 self.app_graph is regenerated
        return self.is_stable()

    def is_stable(self) -> bool:
        """Determine if the graph is in a stable state.

        A stable state is when no destination endpoints (GC inputs) are
        unreferenced (unconnected). If there are unconnected inputs a graph
        cannot be executed.

        Returns
        -------
        True if the graph is in a steady state.
        """
        # TODO: next() in try?
        return not tuple(self.igraph.dst_unref_filter())

    def validate(self, validate_igraph: bool = False) -> bool:  # noqa: C901
        """Check if the graph is valid.

        The graph should be in a steady state before calling.

        This function is not intended to be fast.
        Genetic code graphs MUST obey the following rules:
            1. All connections are referenced at source (except row 'U') and destination
            2. All unreferenced sources are referenced by the unconnected 'U' row.
            3a. REMOVED: All destinations are connected - this is a test of stability.
            3b. All destinations are only connected once.
            4. Types are valid.
            5. Indexes within are contiguous and start at 0.
            6. Constant values are valid.
            7. Row "P" is only defined if "F" is defined.
            8. The rows structure is consistent with the i_graph
            9. Row A is not defined if the graph is for a codon.
            10. All row 'I' endpoints are sources.
            11. All row 'O' & 'P' endpoints are destinations.
            12. Source types are compatible with destination types.
            13a. Rows destinations may only be connected to source rows as defined
                 by gc_graph.src_rows.
            13b. Rows sources may not be connected to the same row or any row in
                 gc_graph.src_rows.
            14. If row 'F' is defined:
                a. Row 'P' must have the same number & type of elements as row 'O'.
                b. Row 'I' must have at least 1 bool source
                c. Row 'F' must have 1 destination
                d. Row 'F' must have no source endpoints
                e. Row 'F' must have 1 bool destination
                f. Row 'B' cannot connect to row 'A'
                g. Row 'P' cannot connect to row 'A'
                h. Row 'O' cannot connect to row 'B'
            15. If row 'U' exists:
                a. Row 'U' must have at least 1 destination endpoint
                b. Row 'U' must have no source endpoints
            16. Internal graph validates
            17. No endpoints have duplicate references

        Args
        ----
        validate_igraph: Validating the igraph is slow. Set to True to so so.

        Returns
        -------
        True if the graph is valid else False.
        If False is returned details of the errors found are in the errors member.
        """
        self.status = []

        # 1.
        for ep in self.igraph.values():
            for ref in ep.refs:
                ref_hash: EndPointHash = ref.force_key(not ep.cls)
                if ref_hash not in self.igraph:
                    self.status.append(text_token({"E01019": {"ep_hash": ep.key(), "ref_hash": ref_hash}}))
                elif ep.row != "U" and end_point_ref(ep.row, ep.idx) not in self.igraph[ref_hash].refs:
                    self.status.append(text_token({"E01020": {"ep_hash": ep.key(), "ref_hash": ref_hash}}))

        # 2.
        unref_srcs: set[src_end_point_ref] = {src_end_point_ref(ep.row, ep.idx) for ep in self.igraph.src_unref_filter()}
        u_refs: set[src_end_point_ref] = {ep.refs[0] for ep in self.igraph.dst_row_filter("U") if ep.refs}
        for unref_src in unref_srcs - u_refs:
            self.status.append(text_token({"E01021": {"ep_hash": unref_src.key()}}))

        # NOTE: This is not a test of validatity but a test of stability
        # 3a.
        # for ep in self.i_graph.dst_unref_filter():
        #    self.status.append(text_token({"E01001": {"ep_hash": ep.key()}}))

        # 3b.
        for ep in self.igraph.dst_filter():
            if len(ep.refs) > 1:
                self.status.append(text_token({"E01018": {"dupe": ep.key(), "refs": ep.refs}}))

        # 4
        for ep in filter(lambda x: not validate(x.typ), self.igraph.values()):
            self.status.append(text_token({"E01002": {"ep_hash": ep.key(), "type_errors": "Does not exist."}}))

        # 5
        for row in ROWS:
            for cls_row, cls_str in (
                (self.igraph.src_row_filter(row), "Src"),
                (self.igraph.dst_row_filter(row), "Dst"),
            ):
                indices: list[int] = sorted((ep.idx for ep in cls_row))
                if [idx for idx in indices if idx not in range(len(indices))]:
                    self.status.append(
                        text_token(
                            {
                                "E01003": {
                                    "cls_str": cls_str,
                                    "row": row,
                                    "indices": indices,
                                }
                            }
                        )
                    )

        # 6
        for ep in filter(lambda x: not validate_value(x.val, x.typ), self.igraph.row_filter("C")):
            self.status.append(
                text_token(
                    {
                        "E01005": {
                            "ref": ep.key(),
                            "value": ep.val,
                            "type": asstr(ep.typ),
                        }
                    }
                )
            )

        # 7
        if "P" in self.rows[DST_EP] and not self.has_row("F"):
            self.status.append(text_token({"E01006": {}}))

        # 8
        for row in ROWS:
            for counter, cls in (
                (self.igraph.num_eps(row, SRC_EP), SRC_EP),
                (self.igraph.num_eps(row, DST_EP), DST_EP),
            ):
                if self.rows[cls].get(row, 0) != counter:
                    self.status.append(
                        text_token(
                            {
                                "E01004": {
                                    "cls_str": ("source", "desintation")[cls],
                                    "row": row,
                                    "row_count": self.rows[cls][row],
                                    "i_count": counter,
                                }
                            }
                        )
                    )

        #  & 9
        # FIXME: It is not possible to tell from the graph whether this is a codon or not

        # 10
        for ep in self.igraph.row_filter("I"):
            if ep.cls != SRC_EP:
                self.status.append(text_token({"E01007": {"ref": ep.key()}}))

        # 11
        for ep in self.igraph.rows_filter(("O", "P")):
            if ep.cls != DST_EP:
                self.status.append(text_token({"E01008": {"ref": ep.key()}}))

        # 12
        for dst_ep in self.igraph.dst_filter():
            for ref in dst_ep.refs:
                src_ep: x_end_point | None = self.igraph.get(ref.key())
                if src_ep is not None and not compatible(src_ep.typ, dst_ep.typ):
                    self.status.append(
                        text_token(
                            {
                                "E01009": {
                                    "ref1": src_ep.key(),
                                    "type1": asstr(src_ep.typ),
                                    "ref2": dst_ep.key(),
                                    "type2": asstr(dst_ep.typ),
                                }
                            }
                        )
                    )
        # 13a
        for ep in self.igraph.dst_filter():
            for ref in ep.refs:
                if ref.row not in VALID_ROW_SOURCES[self.has_row("F")].get(ep.row, tuple()):
                    self.status.append(text_token({"E01010": {"ref1": ep.key(), "ref2": ref.key()}}))

        # 13b
        for ep in self.igraph.src_filter():
            for ref in ep.refs:
                if ref.row not in VALID_ROW_DESTINATIONS[self.has_row("F")][ep.row]:
                    self.status.append(text_token({"E01017": {"ref1": ep.key(), "ref2": ref.key()}}))

        if self.has_row("F"):
            # 14a
            len_p: int = self.igraph.num_eps("P", DST_EP)
            len_o: int = self.igraph.num_eps("O", DST_EP)
            if len_p != len_o:
                self.status.append(text_token({"E01013": {"len_p": len_p, "len_o": len_o}}))
            for o_ep, p_ep in zip(self.igraph.dst_row_filter("O"), self.igraph.dst_row_filter("P")):
                if o_ep.typ != p_ep.typ:
                    self.status.append(text_token({"E01023": {"p_hash": p_ep.key(), "o_hash": o_ep.key()}}))

            # 14b
            if not [ep.typ == asint("bool") for ep in self.igraph.row_filter("I")]:
                self.status.append(text_token({"E01016": {}}))

            # 14c
            if not self.igraph.num_eps("F", DST_EP):
                self.status.append(text_token({"E01024": {}}))

            # 14d
            if self.igraph.num_eps("P", SRC_EP):
                self.status.append(text_token({"E01025": {}}))

            # 14e
            if not [ep.typ == asint("bool") for ep in self.igraph.row_filter("F")]:
                self.status.append(text_token({"E01026": {}}))

        # 15a
        if self.igraph.num_eps("U", SRC_EP):
            self.status.append(text_token({"E01027": {}}))

        # 16
        if validate_igraph and not self.igraph.validate():
            self.status.append(text_token({"E01028": {}}))

        # 17
        for ep in self.igraph.values():
            if len(ep.refs) != len(set(ep.refs)):
                self.status.append(text_token({"E01029": {"ep": ep}}))

        if _LOG_DEBUG:
            if self.status:
                _logger.debug(f"Graph internal format:\n{self}")
                for status in self.status:
                    _logger.debug(str(status))

        return not self.status

    def random_remove_connection(self, num: int = 1) -> None:
        """Randomly choose n connections and remove them.

        n is the number of connections to remove and must be >=0 (0 is
        a no-op). If n is greater than the number of connections all connections are removed.

        Args
        ----
        n: Number of connections to remove.

        This is done by selecting all of the connected destination endpoint not in row U and
        randomly sampling n.
        """
        dst_ep_tuple = tuple(self.igraph.dst_ref_filter())
        if _LOG_DEBUG:
            _logger.debug(f"Selecting connection to remove from destination endpoint tuple: {dst_ep_tuple}")
        if dst_ep_tuple:
            self.remove_connection(sample(dst_ep_tuple, min((len(dst_ep_tuple), num))))

    def remove_connection(self, dst_ep_iter: Iterable[dst_end_point]) -> None:
        """Remove connections to the specified destination endpoints.

        Args
        ----
        dst_ep_seq: An iterable of destination endpoints to disconnect.
        """
        # Row U is the unconnected row and not referenced in the source row (because it is unconnected!)
        for dst_ep in dst_ep_iter:
            if _LOG_DEBUG:
                _logger.debug(f"Removing connection from destination endpoint: {dst_ep}")
                assert dst_ep.row != "U"
            cast(src_end_point, self.igraph[dst_ep.refs[0].key()]).refs.remove(dst_end_point_ref(dst_ep.row, dst_ep.idx))
            dst_ep.refs = []

    def remove_all_connections(self) -> None:
        """Remove all connections.

        This is done by selecting all of the connected destination endpoint not in row U.
        """
        dst_ep_tuple = tuple(self.igraph.dst_ref_filter())
        if _LOG_DEBUG:
            _logger.debug(f"Selecting connection to remove from destination endpoint tuple: {dst_ep_tuple}")
        if dst_ep_tuple:
            self.remove_connection(dst_ep_tuple)

    def random_add_connection(self) -> None:
        """Randomly choose two endpoints to connect.

        This is done by first selecting an unconnected destination endpoint then
        randomly (no filtering) choosing a viable source endpoint.
        """
        dst_ep_tuple = tuple(self.igraph.dst_unref_filter())
        if _LOG_DEBUG:
            _logger.debug(f"Selecting connection to add to destination endpoint list: {dst_ep_tuple}")
        if dst_ep_tuple:
            self.add_connection(choice(dst_ep_tuple))

    def connect_all(self) -> None:
        """Connect all unconnected destination endpoints.

        Find all the unreferenced destination endpoints and connect them to a random viable source.
        If there is no viable source endpoint the destination endpoint will remain unconnected.
        """
        for dst_ep in self.igraph.dst_unref_filter():
            self.add_connection(dst_ep)

    def add_connection(
        self,
        dst_ep: dst_end_point,
        allowed_rows: Sequence[SourceRow] = SOURCE_ROWS,
        unreferenced: bool = False,
    ) -> bool:
        """Add a connection to a random valid source endpoint from the specified destination.

        Args
        ----
        dst_ep: The destination endpoint to connect. Must be unconnected (unreferenced)
        allowed_rows: Further contrain the potential source endpoints to one of these rows.
        unreferenced: Further constrain the source endpoints to consider only unreferenced ones.

        Returns
        -------
        True if the dst_ep was connected to a source else False.
        """
        # NB: Considered moving VALID_SOURCE_ROWS and related to sets but not worth it.
        # Noting here for when I forget and consider it again (python 3.11.2)
        # (venv) shapedsundew9@Jammy:~/Projects$ python3 -m timeit -s "aset = set('ABC')" "'A' in aset"
        # 5000000 loops, best of 5: 85.4 nsec per loop
        # (venv) shapedsundew9@Jammy:~/Projects$ python3 -m timeit -s "atuple = tuple('ABC')" "'A' in atuple"
        # 5000000 loops, best of 5: 85.9 nsec per loop

        if _LOG_DEBUG:
            _logger.debug(f"The destination endpoint requiring a connection: {dst_ep}")

        filter_func = self.igraph.src_unref_filter if unreferenced else self.igraph.src_filter
        eligible_rows = tuple(row for row in VALID_ROW_SOURCES[self.has_row("F")][dst_ep.row] if row in allowed_rows)
        src_eps = tuple(src_ep for src_ep in filter_func() if src_ep.row in eligible_rows and compatible(src_ep.typ, dst_ep.typ))
        if src_eps:
            src_ep: src_end_point = choice(src_eps)
            if _LOG_DEBUG:
                _logger.debug(f"The source endpoint to make the connection: {src_ep}")
            dst_ep.refs = [src_ep.as_ref()]
            src_ep.refs.append(dst_ep.as_ref())
            return True
        if _LOG_DEBUG:
            _logger.debug(f"No viable source endpoints for destination endpoint: {dst_ep}")
        return False

    def row_if(self, row: Row) -> tuple[list[int], list[int]]:
        """Return the row interface definition.

        Args
        ----
        row: One of gc_graph.rows.

        Returns
        -------
        A tuple of lists of integers (src, dst) which are ep_type_ints in the order defined in the graph.
        """
        return (
            [ep.typ for ep in sorted(self.igraph.src_row_filter(row), key=lambda x: x.idx)],
            [ep.typ for ep in sorted(self.igraph.dst_row_filter(row), key=lambda x: x.idx)],
        )

    def connected_row_if(self, row: DestinationRow) -> list[int]:
        """Return the connected input row interface definition.

        Args
        ----
        row: One of gc_graph.rows destination rows.

        Returns
        -------
        List of integers which are ep_type_ints of connected endpoints in the order defined in the graph.
        """
        return [ep.typ for ep in sorted(self.igraph.dst_row_filter(row), key=lambda x: x.idx) if ep.refs]

    def input_if(self) -> list[int]:
        """Return the input interface definition.

        Returns
        -------
        A list of integers which are ep_type_ints in the order defined in the graph.
        """
        # TODO: If the graph has been normalized it would be quicker to get this from the connection graph
        return [ep.typ for ep in sorted(self.igraph.row_filter("I"), key=lambda x: x.idx)]

    def output_if(self) -> list[int]:
        """Return the output interface definition.

        Returns
        -------
        A list of integers which are ep_type_ints in the order defined in the graph.
        """
        # TODO: If the graph has been normalized it would be quicker to get this from the connection graph
        return [ep.typ for ep in sorted(self.igraph.row_filter("O"), key=lambda x: x.idx)]

    def viable_dst_types(self, row: DestinationRow) -> set[int]:
        """Create a tuple of viable destination end point types for row."""
        return {ep.typ for ep in self.igraph.src_rows_filter(VALID_ROW_SOURCES[self.has_row("F")][row])}


def random_gc_graph(validator: base_validator, verify: bool = False, seed: int | None = None) -> gc_graph:
    """Create a random GC graph using the validator as a rules set.

    The validator must be a subset of the rules defined for a valid gc_graph.
    """
    rc_graph: JSONGraph = generate(validator, 1, seed, seed, verify)[0]["graph"]

    # Uniquify source reference indexes to prevent random collisions
    # and find the set of constant types required by the rows below.
    unique = count()
    constant_types = set()
    for row in rc_graph:
        if row != "C":
            rc_graph[row] = [[ref[0], next(unique), ref[2]] for ref in rc_graph[row]]
            constant_types.update((ref[2] for ref in rc_graph[row] if ref[0] == "C"))
    if "F" in rc_graph:
        # O references A and P reference B - to validate they must have the same types. Easiest to duplicate.
        if "A" in rc_graph:
            rc_graph["B"] = deepcopy(rc_graph["A"])
            # Duplicate A & B sources in U to keep symmetry.
            if "U" in rc_graph:
                rc_graph["U"].extend([["B", ref[1], ref[2]] for ref in rc_graph["U"] if ref[0] == "A"])  # type: ignore
                rc_graph["U"].extend([["A", ref[1], ref[2]] for ref in rc_graph["U"] if ref[0] == "B"])  # type: ignore
        if "O" in rc_graph:
            # P destinations are the same as O destinations when F is defined but cannot reference row A (must be B)
            rc_graph["P"] = [[(ref[0], "B")[ref[0] == "A"], ref[1], ref[2]] for ref in rc_graph["O"]]

    new_constants: list[list[str | int]] = [[random_constant_str(typ), typ] for typ in constant_types]
    if new_constants:
        rc_graph["C"] = new_constants
    elif "C" in rc_graph:
        del rc_graph["C"]

    gcg = gc_graph(rc_graph)
    if _LOG_DEBUG:
        _logger.debug(f"Pre-normalized randomly generated internal graph:\n{gcg}")

    gcg.igraph.remove_all_refs()
    gcg.purge_unconnectable_types()
    gcg.reindex()
    gcg.normalize()
    if verify:
        _logger.debug(f"Post-normalized randomly generated internal graph:\n{gcg}")
        assert gcg.validate(True), [str(x) for x in gcg.status]
    return gcg
