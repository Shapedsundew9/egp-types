"""Tools for managing genetic code graphs.

Created Date: Sunday, July 19th 2020, 2:56:11 pm
Author: Shapedsundew9

Description: Genetic code graphs define how genetic codes are connected together. The gc_graph_tools module
defines the rules of the connectivity (the "physics") i.e. what is possible to observe or occur.
"""

from collections import Counter
from copy import deepcopy
from logging import DEBUG, Logger, NullHandler, getLogger
from math import sqrt
from random import choice, randint, sample
from typing import Any, Literal, LiteralString
from pprint import pformat

import gi
from bokeh.io import output_file, save
from bokeh.models import (BoxSelectTool, Circle, ColumnDataSource, HoverTool,
                          LabelSet, MultiLine, NodesAndLinkedEdges, Range1d,
                          TapTool, GraphRenderer)
from bokeh.palettes import Category20_20, Greys9
from bokeh.plotting import figure, from_networkx
from cairo import FONT_WEIGHT_BOLD, FontWeight
from egp_utils.text_token import register_token_code, text_token
from graph_tool import Graph
from graph_tool.draw import graph_draw
from networkx import DiGraph, get_node_attributes, spring_layout, Graph

from .egp_typing import Row, SourceRow, DestinationRow, EndPointType, EndPointClass, EndPointIndex, EndPointHash, SOURCE_ROWS, ROWS, castEndPointIndex, castEndPointType, CPI, VALID_ROW_SOURCES, DESTINATION_ROWS, DST_EP, SRC_EP, ConnectionPoint, ConnectionGraph, EndPoint, EndPointReference, InternalGraph, GCGraphRows, castRow, castDestinationRow, castSourceRow
# Needed to prevent something pulling in GtK 4.0 and graph_tool complaining.
from .ep_type import (EP_TYPE_NAMES, REAL_EP_TYPE_VALUES,
                      UNKNOWN_EP_TYPE_VALUE, asint, asstr, compatible,
                      import_str, type_str, validate)
from .xgc_validator import graph_validator


gi.require_version('Gtk', '3.0')


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


def _REPR_LAMBDA(x: tuple[EndPointHash, EndPoint]) -> EndPointIndex:
    """Extra the end point index from the internal graph dict key,value entry."""
    return x[1].idx


def _DST_FILTER(x: EndPoint) -> bool:
    """True if x is a destination endpoint."""
    return not x.cls


def _ROW_C_FILTER(x: EndPoint) -> bool:
    """True if x is a constant row endpoint."""
    return x.row == 'C'


def _GET_INDEX(x: EndPoint) -> EndPointIndex:
    return x.idx


def _OUT_FUNC(x):
    return x[ep_idx.ROW] == 'O' and x[ep_idx.EP_TYPE] == DST_EP


def _ROW_U_FILTER(x):
    return x[ep_idx.ROW] == 'U'


def _SRC_UNREF_FILTER(x):
    return x[ep_idx.EP_TYPE] == SRC_EP and not x[ep_idx.REFERENCED_BY]


def _DST_UNREF_FILTER(x):
    return x[ep_idx.EP_TYPE] == DST_EP and not x[ep_idx.REFERENCED_BY]


# TODO: Make lambda function definitions static
# TODO: Replace all the little filter functions with static lambda functions.
# TODO: Use EP_TYPE consistently (i.e. not for both EP data type & SRC or DST)

# NetworkX & Bokeh parameters
_NX_NODE_RADIUS: Literal[30] = 30
_NX_NODE_FONT: Literal['courier'] = 'courier'
_NX_HOVER_TOOLTIPS: list[tuple[str, str]] = [("Type", "@type"), ("Value", "@value"), ("EP Type", "@ep_type")]
_NX_ROW_EDGE_ATTR: dict[str, str] = {
    'line': Greys9[4],
    'select': Greys9[0],
    'hover': Greys9[0]
}
_NX_CODON_NODE_ATTR: dict[str, str] = {'fill': Category20_20[15], 'select': Category20_20[14],
                                       'hover': Category20_20[14], 'line': Greys9[0], 'label': 'Codon'}
_NX_ROW_NODE_ATTR: dict[Row, dict[str, str]] = {
    'I': {'fill': Greys9[8], 'select': Greys9[7], 'hover': Greys9[7], 'line': Greys9[0], 'label': 'I'},
    'C': {'fill': Category20_20[11], 'select': Category20_20[10], 'hover': Category20_20[10], 'line': Greys9[0], 'label': 'C'},
    'A': {'fill': Category20_20[7], 'select': Category20_20[6], 'hover': Category20_20[6], 'line': Greys9[0], 'label': 'A'},
    'B': {'fill': Category20_20[1], 'select': Category20_20[0], 'hover': Category20_20[0], 'line': Greys9[0], 'label': 'B'},
    'F': {'fill': Category20_20[13], 'select': Category20_20[12], 'hover': Category20_20[12], 'line': Greys9[0], 'label': 'F'},
    'O': {'fill': Greys9[5], 'select': Greys9[4], 'hover': Greys9[4], 'line': Greys9[0], 'label': 'O'},
    'P': {'fill': Category20_20[5], 'select': Category20_20[4], 'hover': Category20_20[4], 'line': Greys9[0], 'label': 'P'},
    'U': {'fill': Category20_20[17], 'select': Category20_20[16], 'hover': Category20_20[16], 'line': Greys9[0], 'label': 'U'},
}
for k, v in _NX_ROW_NODE_ATTR.items():
    v['font'] = _NX_NODE_FONT


# Graph Tool parameters
_GT_NODE_DIAMETER: Literal[60] = 60
_GT_NODE_SHAPE: Literal['circle'] = 'circle'
_GT_NODE_FONT_SIZE: Literal[14] = 14
_GT_NODE_FONT_WEIGHT: FontWeight = FONT_WEIGHT_BOLD
_GT_ROW_NODE_ATTR: dict[Row, dict[str, Any]] = {
    'I': {'fill_color': [1.0, 1.0, 1.0, 1.0], 'text': 'I'},
    'C': {'fill_color': [0.5, 0.5, 0.5, 1.0], 'text': 'C'},
    'F': {'fill_color': [0.0, 1.0, 1.0, 1.0], 'text': 'F'},
    'A': {'fill_color': [1.0, 0.0, 0.0, 1.0], 'text': 'A'},
    'B': {'fill_color': [0.0, 0.0, 1.0, 1.0], 'text': 'B'},
    'P': {'fill_color': [0.0, 1.0, 0.0, 1.0], 'text': 'P'},
    'O': {'fill_color': [0.0, 0.0, 0.0, 1.0], 'text': 'O'},
    'U': {'fill_color': [0.0, 1.0, 0.0, 1.0], 'text': 'U'}
}
for k, v in _GT_ROW_NODE_ATTR.items():
    v['size'] = _GT_NODE_DIAMETER
    v['shape'] = _GT_NODE_SHAPE
    v['font_size'] = _GT_NODE_FONT_SIZE
    v['font_weight'] = _GT_NODE_FONT_WEIGHT

_GT_EDGE_PEN_WIDTH: Literal[4] = 4
_GT_EDGE_MARKER_SIZE: Literal[24] = 24


register_token_code('E01000', 'A graph must have at least one output.')
register_token_code('E01001', '{ep_type} endpoint {ref} is not connected to anything.')
register_token_code('E01002', '{ep_type} endpoint {ref} does not have a valid type: {type_errors}.')
register_token_code('E01003', 'Row {row} does not have contiguous indices starting at 0: {indices}.')
register_token_code('E01004', 'The references to row {row} are not contiguous indices starting at 0: {indices}.')
register_token_code('E01005', 'Constant {ref} does not have a valid value ({value}) for type {type}.')
register_token_code('E01006', 'If row "F" is defined then row "P" must be defined.')
register_token_code('E01007', 'Endpoint {ref} must be a source.')
register_token_code('E01008', 'Endpoint {ref} must be a destination.')
register_token_code(
    'E01009', 'Source endpoint {ref1} type {type1} is not compatible with destination endpoint {ref2} type {type2}.')
register_token_code('E01010', 'Destination endpoint {ref1} cannot be connected to source endpoint {ref2}.')
register_token_code('E01011', 'Destination endpoint {ref1} cannot be connected to source endpoint {ref2} when row "F" exists.')
register_token_code('E01012', 'Endpoint {ref1} cannot reference row B {ref2} if "F" is defined.')
register_token_code('E01013', 'Row "P" length ({len_p}) must be the same as row "O" length ({len_o}) when "F" is defined.')
register_token_code('E01014', 'Row "U" endpoint {u_ep} referenced by more than one endpoint {refs}.')
register_token_code('E01015', 'Row "U" endpoint {u_ep} references a constant that does not exist {refs}.')
register_token_code('E01016', 'Row "I" must contain at least one bool type source endpoint if "F" is defined.')
register_token_code('E01017', 'Source endpoint {ref1} cannot be connected to destination endpoint {ref2}.')
register_token_code('E01018', 'Destination endpoint {dupe} is connected to multiple sources {refs}.')

register_token_code('I01000', '"I" row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01001', '"I" row endpoint removed.')
register_token_code('I01100', '"A" source row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01101', '"A" source row endpoint removed.')
register_token_code('I01102', '"A" destination row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01103', '"A" destination row endpoint removed.')
register_token_code('I01200', '"B" source row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01201', '"B" source row endpoint removed.')
register_token_code('I01202', '"B" destination row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01203', '"B" destination row endpoint removed.')
register_token_code('I01302', '"O" row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01303', '"O" row endpoint removed.')
register_token_code('I01402', '"P" row endpoint appended of UNKNOWN_EP_TYPE_VALUE.')
register_token_code('I01403', '"P" row endpoint removed.')

register_token_code('I01900', 'No source endpoints in the list to remove.')


# FIXME: Why is this here & not in ep_type.py?
def validate_value(value_str, ep_type_int):
    """Validate the executable string is a valid ep_type value.

    Args
    ----
        value_str (str): As string that when executed as the RHS of an assignment returns a value of ep_type
        ep_type_int (int): An Endpoint Type Definition (see ref).

    Returns
    -------
        bool: True if valid else False
    """
    tstr = type_str(ep_type_int)
    try:
        eval(tstr)
    except NameError:
        if _LOG_DEBUG:
            _logger.debug(f'Importing {tstr}.')
        exec(import_str(ep_type_int))

    if _LOG_DEBUG:
        _logger.debug(f'retval = isinstance({value_str}, {tstr})')
    try:
        retval = eval(f'isinstance({value_str}, {tstr})')
    except (NameError, SyntaxError):
        return False
    return retval


# TODO: Consider caching calculated results.
class gc_graph():
    """Manipulating Genetic Code Graphs."""
    __slots__ = ('i_graph', 'rows', 'app_graph', 'status')
    i_graph: InternalGraph
    rows: GCGraphRows
    app_graph: Any
    status: Any

    def __init__(self, c_graph: ConnectionGraph = dict(), i_graph: InternalGraph = dict()) -> None:

        self.i_graph = i_graph if i_graph else self._convert_to_internal(c_graph)
        self.rows = (dict(Counter([ep.row for ep in self.i_graph.values() if not ep.cls])),
                     dict(Counter([ep.row for ep in self.i_graph.values() if ep.cls])))

    def __repr__(self) -> str:
        """Print the graph in row order sources then destinations in index order."""
        # NOTE: This function is used in determining the signature of a GC.
        str_list: list[str] = []
        for row in ROWS:
            for ep_class in (False, True):
                row_dict: dict[str, EndPoint] = {k: v for k, v in self.i_graph.items() if v.cls == ep_class and v.row == row}
                str_list.extend(["'" + k + "': " + str(v) for k, v in sorted(row_dict.items(), key=_REPR_LAMBDA)])
        return ', '.join(str_list)

    def _convert_to_internal(self, c_graph: ConnectionGraph) -> InternalGraph:
        """Convert graph to internal format.

        The internal format allows quicker searching for parameters by type, endpoint type etc.
        It maintains bi-directional references for quick manipulation.
        Types are stored in integer format for efficiency.
        """
        i_graph: InternalGraph = {}
        for row, cps in c_graph.items():
            for index, cp in enumerate(cps):
                if row != 'C':
                    cp_row: Row = castRow(cp[CPI.ROW])
                    cp_idx: EndPointIndex = castEndPointIndex(cp[CPI.IDX])
                    cp_typ: EndPointType = castEndPointType(cp[CPI.TYP])
                    dst_ep: EndPoint = EndPoint(DST_EP, row, index, cp_typ, [EndPointReference(cp_row, cp_idx)])
                    i_graph[dst_ep.key()] = dst_ep
                    src_ep_hash: EndPointHash = dst_ep.refs[0].key(SRC_EP)
                    if src_ep_hash in i_graph:
                        i_graph[src_ep_hash].refs.append(EndPointReference(row, index))
                    elif cp_row != 'C':
                        refs: list[EndPointReference] = [EndPointReference(row, index)] if row != 'U' else []
                        i_graph[src_ep_hash] = EndPoint(SRC_EP, cp_row, cp_idx, cp_typ, refs)
                else:
                    src_ep: EndPoint = EndPoint(SRC_EP, row, index, castEndPointType(cp[CPI.CTYP]), [], cp[CPI.CTYP])
                    i_graph[src_ep.key()] = src_ep
        return i_graph

    def _add_ep(self, ep: EndPoint) -> None:
        """Add an endpoint to the internal graph format structure."""
        row_counts: dict[str, int] = self.rows[ep.cls]
        if ep.row not in self.rows[ep.cls]:
            row_counts[ep.row] = 0
        ep.idx = row_counts[ep.row]
        self.i_graph[ep.key()] = ep
        row_counts[ep.row] += 1

    def _remove_ep(self, ep: EndPoint, check: bool = True) -> None:
        """Remove an endpoint to the internal graph format structure.

        Args
        ----
            ep: An endpoint list structure to be removed from the internal graph.
            check: Only remove end point if it is unreferenced when true.
        """
        if not check or not ep.refs:
            del self.i_graph[ep.key()]
            self.rows[ep.cls][ep.row] -= 1

    def connection_graph(self) -> ConnectionGraph:
        """Convert graph to GMS graph (Connection Graph) format."""
        graph: ConnectionGraph = {}
        for ep in sorted(filter(_DST_FILTER, self.i_graph.values()), key=_GET_INDEX):
            row: Row = ep.row
            if row not in graph:
                graph[row] = []
            if ep.refs:
                graph[row].append([ep.refs[0].row, ep.refs[0].idx, ep.typ])
        for ep in sorted(filter(_ROW_C_FILTER, self.i_graph.values()), key=_GET_INDEX):
            if 'C' not in graph:
                graph['C'] = []
            graph['C'].append([ep.typ, ep.val])
        if _LOG_DEBUG and not graph_validator.validate({'graph': graph}):
            raise ValueError(f"Connection graph is not valid:\n{pformat(graph, indent=4)}\n\n{graph_validator.error_str()}")
        return graph

    def nx_graph(self) -> DiGraph:
        """Create a directed networkx graph treating each destination endpoint as a unique node.

        NetworkX is used because of its integration with Bokeh.
        Bokeh has limited graph drawing capabilities. Specifically it cannot handle multiple edges
        between the same nodes nor indicating direction of edges. However it has good interactions.

        Returns
        -------
        DiGraph: A networkX direction graph of the GC graph.
        There are three types of vertices:
            row: Each row (with the single exception of 'C') has a single vertex with an area
                proportional to the number of total number of endpoints in the row.
            endpoint: Each endpoint is represented by a node thus:
                A row has a set of source endpoint vertices connected to it
                A row has a set of destination endpoint vertices connected to it
                NOTE: The constant row is only represented as a set of endpoint vertices.
            codon: If the graph is of a codon i.e. there are no rows A, B or C then a codon vertex is
                added to connect any inputs & outputs to.
        Connections between rows are represented by edges between endpoint vertices.
        """
        nx_graph: DiGraph = DiGraph()
        gtg: dict[str, dict[bool, dict[int, str]]] = {k: {SRC_EP: {}, DST_EP: {}} for k in ROWS}
        for ep in self.i_graph.values():
            if ep.row not in nx_graph.nodes:
                size: int = round(_NX_NODE_RADIUS * sqrt(float(self.rows[SRC_EP].get(ep.row, 0) + self.rows[DST_EP].get(ep.row, 0))))
                nx_graph.add_node(ep.row, text=ep.row, size=size, font_size='28px',
                                  x_offset=-8, y_offset=-19, type='GC', ep_type='N/A', value='N/A',
                                  **_NX_ROW_NODE_ATTR[ep.row])
            if ep.idx not in gtg[ep.row][ep.cls]:
                row: LiteralString = ep.row if ep.cls else ep.row.lower()
                node: str = row + str(ep.idx)
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to nx_graph node: {node}")
                ep_type: Literal['Destination', 'Source'] = ('Destination', 'Source')[ep.cls]
                value: Any = ep.val if ep.row == 'C' else 'N/A'
                nx_graph.add_node(node, text=node, size=_NX_NODE_RADIUS, font_size='16px',
                                  x_offset=-9, y_offset=-11, type=asstr(ep.typ),
                                  ep_type=ep_type, value=value, **_NX_ROW_NODE_ATTR[ep.row])
                data: tuple[str, str] = (ep.row, node) if ep.cls else (node, ep.row)
                nx_graph.add_edge(*data, **_NX_ROW_EDGE_ATTR)
                gtg[ep.row][ep.cls][ep.idx] = node
        for ep in filter(self.dst_filter(), self.i_graph.values()):
            for ref in ep.refs:
                dst_node: str = gtg[ep.row][DST_EP][ep.idx]
                src_node: str = gtg[ref.row][SRC_EP][ref.idx]
                nx_graph.add_edge(src_node, dst_node, **_NX_ROW_EDGE_ATTR)
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to nx_graph edge : {src_node}->{dst_node}")
        return nx_graph

    def nx_draw(self, path: str = "./nx_graph", size: tuple[int, int] = (1600, 900)) -> None:
        """Draw the directed networkx graph where each destination endpoint as a unique node.

        Args
        ----
        path: Folder plus base file name of the output image. '.html' will be appended.
        size: Tuple of x, y output image dimensions.
        """
        nx_graph: DiGraph = self.nx_graph()
        plot: figure = figure(plot_width=size[0], plot_height=size[1],
                              tools="pan,wheel_zoom,save,reset", active_scroll='wheel_zoom',
                              title="Erasmus GP GC Internal Graph", x_range=Range1d(-110.1, 110.1), y_range=Range1d(-110.1, 110.1))
        plot.add_tools(HoverTool(tooltips=_NX_HOVER_TOOLTIPS, anchor='top_right'), TapTool(), BoxSelectTool())
        bk_graph: GraphRenderer = from_networkx(nx_graph, spring_layout, scale=100, center=(0, 0))
        bk_graph.node_renderer.glyph = Circle(line_color='line', size='size', fill_color="fill")
        bk_graph.node_renderer.selection_glyph = Circle(line_color='line', size='size', fill_color="select")
        bk_graph.node_renderer.hover_glyph = Circle(line_color='line', size='size', fill_color="hover")
        bk_graph.edge_renderer.glyph = MultiLine(line_color="line", line_alpha=0.8, line_width=2)
        bk_graph.edge_renderer.selection_glyph = MultiLine(line_color="select", line_width=3)
        bk_graph.edge_renderer.hover_glyph = MultiLine(line_color="hover", line_width=3)
        bk_graph.selection_policy = NodesAndLinkedEdges()
        bk_graph.inspection_policy = NodesAndLinkedEdges()
        plot.renderers.append(bk_graph)

        x, y = zip(*bk_graph.layout_provider.graph_layout.values())
        node_labels = get_node_attributes(nx_graph, 'text')
        label_x_offsets = get_node_attributes(nx_graph, 'x_offset')
        label_y_offsets = get_node_attributes(nx_graph, 'y_offset')
        label_font_sizes = get_node_attributes(nx_graph, 'font_size')
        label_font = get_node_attributes(nx_graph, 'font')
        source = ColumnDataSource({
            'x': x,
            'y': y,
            'text': list(node_labels.values()),
            'x_offset': list(label_x_offsets.values()),
            'y_offset': list(label_y_offsets.values()),
            'font_size': list(label_font_sizes.values()),
            'font': list(label_font.values())
        })
        labels = LabelSet(x='x', y='y', text='text',
                          source=source, text_font_size='font_size', x_offset='x_offset', y_offset='y_offset',
                          text_font='font', text_font_style='bold', text_color='black')
        plot.renderers.append(labels)
        output_file(f"{path}.html", title="Erasmus GP GC Internal Graph")
        save(plot)

    def gt_graph(self):
        """Create a graph_tool graph treating rows as nodes.

        graph_tool is used because its drawing capabilities allow for multiple edges between nodes (unlike Bokeh)
        though it has much more limited interactions.

        Returns
        -------
            (Graph): A graph_tool Graph object.
            (dict): Dict of vertex properties.
            (dict): Dict of edge properties.
        """
        g = Graph()
        node_p = {
            'text': g.new_vertex_property('string'),
            'shape': g.new_vertex_property('string'),
            'fill_color': g.new_vertex_property('vector<float>'),
            'size': g.new_vertex_property('int'),
            'font_size': g.new_vertex_property('int'),
            'font_weight': g.new_vertex_property('int')
        }
        edge_p = {
            'pen_width': g.new_edge_property('int'),
            'marker_size': g.new_edge_property('int')
        }
        gtg = {}
        for row in gc_graph.rows:
            dst_list = list(filter(self.dst_filter(self.row_filter(row)), self.i_graph.values()))
            src_list = list(filter(self.src_filter(self.row_filter(row)), self.i_graph.values()))
            size = max((len(dst_list), len(src_list)))
            if size:
                node = g.add_vertex()
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to gt_graph node: {row}")
                for k, v in _GT_ROW_NODE_ATTR[row].items():
                    node_p[k][node] = v
                node_p['size'][node] = round(node_p['size'][node] * sqrt(size))
                node_p['font_size'][node] = round(node_p['font_size'][node] * sqrt(size))
                gtg[row] = node
            for ep in dst_list:
                dst_row = ep.row
                src_row = ep.refs[0][ref_idx.ROW]
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to gt_graph edge: {src_row}->{dst_row}")
                edge = g.add_edge(gtg[src_row], gtg[dst_row])
                edge_p['pen_width'][edge] = _GT_EDGE_PEN_WIDTH
                edge_p['marker_size'][edge] = _GT_EDGE_MARKER_SIZE
        return g, node_p, edge_p

    def gt_draw(self, path="./gt_graph", size=(1600, 900)):
        """Draw the graph_tool row node graph.

        Args
        ----
            path (str): folder plus base file name of the output image. '.png' will be appended.
            size ((int, int)): Tuple of x, y output image dimensions.
        """
        g, n, e = self.gt_graph()
        graph_draw(g, vertex_text=n['text'], vertex_shape=n['shape'],
                   vertex_fill_color=n['fill_color'], vertex_size=n['size'],
                   vertex_font_weight=n['font_weight'], vertex_font_size=n['font_size'],
                   edge_pen_width=e['pen_width'], edge_marker_size=e['marker_size'],
                   output=path + ".png", output_size=size)

    def draw(self, path='./graph', size=(1600, 900)):
        """Draw both the nx_graph & the gt_graph.

        Args
        ----
            path (str): folder plus base file name of the output image.
                        '.png' will be appended to the gt_graph.
                        '.html' will be appended to the nx_graph.
            size ((int, int)): Tuple of x, y output image dimensions.
        """
        if _LOG_DEBUG:
            _logger.debug(f"Graph to draw:\n{self}")
        self.gt_draw(path, size)
        self.nx_draw(path, size)

    def add_input(self, ep_type=None):
        """Create and append an unconnected row I endpoint.

        Args
        ----
        ep_type (int): ep_type in integer format. If None a random
            real ep_type is chosen.
        """
        if ep_type is None:
            ep_type = choice(REAL_EP_TYPE_VALUES)
        i_index = self.rows[SRC_EP].get('I', 0)
        self._add_ep([SRC_EP, 'I', i_index, ep_type, []])

    def remove_input(self, idx=None):
        """Remove input idx.

        No-op if there are no inputs.

        Args
        ----
        idx (int): Index of input to remove. If None a random index is chosen.
        """
        num_inputs = self.rows[SRC_EP].get('I', 0)
        if num_inputs:
            if idx is None:
                idx = randint(0, num_inputs - 1)
            ep_ref = ['I', idx]
            if _LOG_DEBUG:
                _logger.debug(f"Removing input {ep_ref}.")
            ep = self.i_graph[hash_ref(ep_ref, SRC_EP)]
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[hash_ref(ref, DST_EP)][ep_idx.REFERENCED_BY].remove(ep_ref)

            # Only re-index row I if it was not the last endpoint that was removed (optimisation)
            if idx != num_inputs - 1:
                self.reindex_row('I')

    def add_output(self, ep_type=None):
        """Create and append an unconnected row O endpoint.

        Args
        ----
        ep_type (int): ep_type in integer format. If None a random
            real ep_type is chosen.
        """
        if ep_type is None:
            ep_type = choice(REAL_EP_TYPE_VALUES)
        o_index = self.rows[DST_EP]['O']
        ep = [DST_EP, 'O', o_index, ep_type, []]
        self._add_ep(ep)
        if self.has_f():
            ep = [DST_EP, 'P', o_index, ep_type, []]
            self._add_ep(ep)

    def remove_output(self, idx=None):
        """Remove output idx.

        No-op if there are no outputs.

        Args
        ----
        idx (int): Index of output to remove. If None a random index is chosen.
        """
        num_outputs = self.rows[DST_EP].get('O', 0)
        if num_outputs:
            if idx is None:
                idx = randint(0, num_outputs - 1)
            ep_ref = ['O', idx]
            if _LOG_DEBUG:
                _logger.debug(f"Removing output {ep_ref}.")
            ep = self.i_graph[hash_ref(ep_ref, DST_EP)]
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[hash_ref(ref, SRC_EP)][ep_idx.REFERENCED_BY].remove(ep_ref)

            # If F exists then must deal with P
            if self.has_f():
                ep_ref = ['P', idx]
                if _LOG_DEBUG:
                    _logger.debug(f"Removing output {ep_ref}.")
                ep = self.i_graph[hash_ref(ep_ref, DST_EP)]
                self._remove_ep(ep, False)
                for ref in ep.refs:
                    self.i_graph[hash_ref(ref, SRC_EP)][ep_idx.REFERENCED_BY].remove(ep_ref)

            # Only re-index row O if it was not the last endpoint that was removed (optimisation)
            if idx != num_outputs - 1:
                self.reindex_row('O')
                if self.has_f():
                    self.reindex_row('P')

    def remove_constant(self, idx=None):
        """Remove constant idx.

        No-op if there are no constants.

        Args
        ----
        idx (int): Index of constant to remove. If None a random index is chosen.
        """
        num_constants = self.rows[SRC_EP].get('C', 0)
        if num_constants:
            if idx is None:
                idx = randint(0, num_constants - 1)
            ep_ref = ['C', idx]
            if _LOG_DEBUG:
                _logger.debug(f"Removing constant {ep_ref}.")
            ep = self.i_graph[hash_ref(ep_ref, SRC_EP)]
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[hash_ref(ref, DST_EP)][ep_idx.REFERENCED_BY].remove(ep_ref)

            # Only re-index row C if it was not the last endpoint that was removed (optimisation)
            if idx != num_constants - 1:
                self.reindex_row('C')

    def add_inputs(self, inputs):
        """Create and add unconnected row I endpoints.

        Will replace any existing endpoints with the same index.

        Args
        ----
        inputs (iterable): ep_types in integer format.
        """
        for index, i in enumerate(inputs):
            self._add_ep([SRC_EP, 'I', index, i, []])

    def add_outputs(self, outputs):
        """Create and add unconnected row O endpoints.

        Will replace any existing endpoints with the same index.

        Args
        ----
        outputs (iteratble): ep_types in integer format.
        """
        for index, i in enumerate(outputs):
            self._add_ep([DST_EP, 'O', index, i, []])

    def endpoint_filter(self, ep_type, filter_func=lambda x: True):
        """Define a filter that only returns endpoints which have endpoint type == ep_type.

        Args
        ----
            ep_type (bool): True == source, False == Destination
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.

        Returns
        -------
            (func): A function for a filter() that will return only endpoints with a type == ep_type.
        """
        return lambda x: x[ep_idx.EP_TYPE] == ep_type and filter_func(x)

    def src_filter(self, filter_func=lambda x: True):
        """Define a filter that only returns endpoints of source type.

        Args
        ----
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.

        Returns
        -------
            (func): A function for a filter() that will return only source endpoints.
        """
        return lambda x: x[ep_idx.EP_TYPE] and filter_func(x)

    def dst_filter(self, filter_func=lambda x: True, include_U=True):
        """Define a filter that only returns endpoints of destination type.

        Args
        ----
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.

        Returns
        -------
            (func): A function for a filter() that will return only destination endpoints.
        """
        if include_U:
            def retval(x): return not x[ep_idx.EP_TYPE] and filter_func(x)
        else:
            def retval(x): return not x[ep_idx.EP_TYPE] and x[ep_idx.ROW] != 'U' and filter_func(x)
        return retval

    def src_row_filter(self, row, filter_func=lambda x: True):
        """Define a filter that only returns endpoints on source rows for the specified row.

        Args
        ----
            row (string): A destination row i.e. one of ('A', 'B', 'F', 'O', 'P')
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.

        Returns
        -------
            (func): A function for a filter() that will return only source endpoints.
        """
        if self.has_f():
            if row == 'B':
                src_rows = gc_graph.src_rows['A']
            elif row == 'O':
                src_rows = gc_graph.src_rows['B']
            else:
                src_rows = gc_graph.src_rows[row]
        else:
            src_rows = gc_graph.src_rows[row]

        return lambda x: x[ep_idx.EP_TYPE] and x[ep_idx.ROW] in src_rows and filter_func(x)

    def rows_filter(self, rows, filter_func=lambda x: True):
        """Define a filter that only returns endpoints in that are in a row in rows.

        Args
        ----
            rows (iter): An iterable of valid row labels i.e. in gc_graph.rows
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.

        Returns
        -------
            (func): A function for a filter() that will return endpoints in 'rows'.
        """
        return lambda x: any(map(lambda p: p == x[ep_idx.ROW], rows)) and filter_func(x)

    def row_filter(self, row, filter_func=lambda x: True):
        """Define a filter that only returns endpoints in that are in a specific row.

        Args
        ----
            row (string): A string from rows.
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.

        Returns
        -------
            (func): A function for a filter() that will return endpoints in 'row'.
        """
        return lambda x: x[ep_idx.ROW] == row and filter_func(x)

    def type_filter(self, ep_types, filter_func=lambda x: True, exact=True):
        """Define a filter that only returns endpoints with a ep_type in 'ep_types'.

        Args
        ----
            ep_types (iter): An iterable of valid ep_types
            filter_func (func): A second filter to be applied. This allows *_filter methods
            to be stacked.
            exact: If True only endpoints with types exactly matching 'ep_types'. If False types
            that have a non-zero affinity will also be returned.

        Returns
        -------
            (func): A function for a filter() that will return endpoints with qualifying 'ep_types'.
        """
        return lambda x: any(map(lambda p: p == x[ep_idx.TYPE], ep_types)) and filter_func(x)

    def unreferenced_filter(self, filter_func=lambda x: True):
        """Define a filter that only returns unreferenced endpoints.

        Returns
        -------
            (func): A function for a filter() that will return unreferenced endpoints.
        """
        return lambda x: not x[ep_idx.REFERENCED_BY] and filter_func(x)

    def referenced_filter(self, filter_func=lambda x: True):
        """Define a filter that only returns referenced endpoints.

        Returns
        -------
            (func): A function for a filter() that will return referenced endpoints.
        """
        return lambda x: x[ep_idx.REFERENCED_BY] and filter_func(x)

    def ref_filter(self, ref):
        """Define a filter that only returns the endpoint at ref.

        Args
        ----
            ref ([row, index]): A genetic code graph endpoint reference.

        Returns
        -------
            (func): A function for a filter() that will return the endpoint 'ref'.
        """
        return lambda x: x[ep_idx.ROW] == ref.row and x[ep_idx.INDEX] == ref.idx

    def _num_eps(self, row, ep_type):
        """Return the number of ep_type endpoints in row.

        If the effective logger level is DEBUG then a self consistency check is done.

        Args
        ----
        row (str): One of gc_graph.rows.
        ep_type (bool): DST_EP or SRC_EP

        Returns
        -------
        (int): Count of the specified endpoints.
        """
        if _LOG_DEBUG:
            count = len(list(filter(self.row_filter(row, self.endpoint_filter(ep_type)), self.i_graph.values())))
            record = self.rows[ep_type].get(row, 0)
            if count != record:
                _logger.warning(
                    'Number of endpoints in {} row "{}" of gc_graph inconsistent: Counted {} recorded {}.'.format(
                        ('destination', 'source')[ep_type], row, count, record))
        return self.rows[ep_type].get(row, 0)

    def has_a(self):
        """Test if row A is defined in the graph.

        If not then this graph is for a codon.

        Returns
        -------
            (bool): True if row A exists.
        """
        return bool(self._num_eps('A', SRC_EP)) or bool(self._num_eps('A', DST_EP))

    def has_f(self):
        """Test if this is a flow control graph.

        Returns
        -------
            (bool): True if row 'F' is defined.
        """
        return bool(self._num_eps('F', DST_EP))

    def has_b(self):
        """Test if row B is defined in the graph.

        Returns
        -------
            (bool): True if row B exists.
        """
        return bool(self._num_eps('B', SRC_EP)) or bool(self._num_eps('B', DST_EP))

    def num_inputs(self):
        """Return the number of inputs to the graph.

        Returns
        -------
            (int): The number of graph inputs.
        """
        return self._num_eps('I', SRC_EP)

    def num_outputs(self):
        """Return the number of outputs from the graph.

        Returns
        -------
            (int): The number of graph outputs.
        """
        return self._num_eps('O', DST_EP)

    def reindex_row(self, row):
        """Re-index row.

        If end points have been removed from a row the row will need
        reindexing so the indicies are contiguous (starting at 0).

        Rows A & B cannot be reindexed as their interfaces are bound to
        a GC definition.

        Args
        ----
        row (str): One of 'ICPUO'
        """
        # Make a list of all the indices in row
        def row_filter(x): return x[ep_idx.ROW] == row
        c_set = [ep.idx for ep in filter(row_filter, self.i_graph.values())]
        # Map the indices to a contiguous integer sequence starting at 0
        r_map = {idx: i for i, idx in enumerate(c_set)}
        # For each row select all the endpoints and iterate through the references to them
        # For each reference update: Find the reverse reference and update it with the new index
        # Finally update the index in the endpoint
        # TODO: Do we need to re-create this filter?
        for ep in filter(row_filter, tuple(self.i_graph.values())):
            if _LOG_DEBUG:
                _logger.debug(f"References to re-index: {ep.refs}")
            for refs in ep.refs:
                for refd in self.i_graph[hash_ref(refs, not ep.cls)][ep_idx.REFERENCED_BY]:
                    if refd[ref_idx.ROW] == row and refd[ref_idx.INDEX] == ep.idx:
                        refd[ref_idx.INDEX] = r_map[ep.idx]
            del self.i_graph[hash_ep(ep)]
            ep.idx = r_map[ep.idx]
            self.i_graph[hash_ep(ep)] = ep

    def normalize(self, removed=False):
        """Make the graph consistent.

        The make the graph consistent the following operations are performed:
            1. Connect all destinations to existing sources if possible
            2. Create new inputs for any destinations that are still unconnected.
            3. Purge any unconnected constants & inputs.
            4. Reference all unconnected sources in row 'U'
            5. self.app_graph is regenerated
            6. Check a valid steady state has been achieved
        """
        _logger.debug("Normalising...")

        # Remove all references to U before starting
        row_u_tuple = tuple(filter(_ROW_U_FILTER, self.i_graph.values()))
        for ep in row_u_tuple:
            self._remove_ep(ep, check=False)
        for ep in self.i_graph.values():
            references = ep.refs
            for idx, ref in enumerate(references):
                if ref.row == 'U':
                    del references[idx]

        # 1 Connect all destinations to existing sources if possible
        self.connect_all()

        # 4 Reference all unconnected sources in row 'U'
        # First remove all existing row U endpoints
        # Then any references to them
        # Finally add the new unreferenced connections.
        unref = tuple(filter(_SRC_UNREF_FILTER, self.i_graph.values()))
        for i, ep in enumerate(unref):
            self._add_ep([DST_EP, 'U', i, ep.typ, [[*ep[1:3]]]])
            ep.refs = [['U', i]]

        # 5 self.app_graph is regenerated
        self.app_graph = self.connection_graph()

        # 6 Check a valid steady state has been achieved
        return self.is_stable()

    def is_stable(self):
        """Determine if the graph is in a stable state.

        A stable state is when no destination endpoints (GC inputs) are
        unreferenced (unconnected). If there are unconnected inputs a graph
        cannot be executed.

        Returns
        -------
            (bool): True if the graph is in a steady state.
        """
        return not tuple(filter(_DST_UNREF_FILTER, self.i_graph.values()))

    def validate(self, codon=False):   # noqa: C901
        """Check if the graph is valid.

        The graph should be in a steady state before calling.

        This function is not intended to be fast.
        Genetic code graphs MUST obey the following rules:
            1. DEPRECATED: Have at least 1 output in 'O'.
            2. a. All sources are connected or referenced by the unconnected 'U' row.
               b. 'U' row endpoints may only be referenced once
               c. 'U' row cannot reference a non-existent constant
            3a. All destinations are connected.
            3b. All destinations are only connected once.
            4. Types are valid.
            5. Indexes within are contiguous and start at 0.
            6. Constant values are valid.
            7. Row "P" is only defined if "F" is defined.
            8. Row A is defined if the graph is not for a codon.
            9. Row A is not defined if the graph is for a codon.
            10. All row 'I' endpoints are sources.
            11. All row 'O' & 'P' endpoints are destinations.
            12. Source types are compatible with destination types.
            13a. Rows destinations may only be connected to source rows as defined
                 by gc_graph.src_rows.
            13b. Rows sources may not be connected to the same row or any row in
                 gc_graph.src_rows.
            14. If row 'F' is defined:
                a. Row 'B' cannot reference row A.
                b. Row 'B' cannot be referenced in row 'O'.
                c. Row 'P' must have the same number & type of elements as row 'O'.
                d. Row 'I' must have at least 1 bool source

        Args
        ----
            codon (bool): Set to True if the graph is for a codon genetic code.

        Returns
        -------
            (bool): True if the graph is valid else False.
            If False is returned details of the errors found are in the errors member.
        """
        self.status = []

        # 1
        # if self.num_outputs() == 0:
        #    self.status.append(text_token({'E01000': {}}))

        # 2a.
        for row in filter(self.src_filter(self.unreferenced_filter()), self.i_graph.values()):
            refs = [ep.refs[0] for ep in filter(self.row_filter('U'), self.i_graph.values())]
            if not any([row[ep_idx.ROW] == r and row[ep_idx.INDEX] == i for r, i in refs]):
                self.status.append(text_token({'E01001': {'ep_type': ['Destination', 'Source'][row[ep_idx.EP_TYPE]],
                                                          'ref': [row[ep_idx.ROW], row[ep_idx.INDEX]]}}))

        # 2b.
        for ep in filter(self.row_filter('U'), self.i_graph.values()):
            if len(ep.refs) > 1:
                self.status.append(text_token({'E01014': {'u_ep': [*ep[1:3]], 'refs': ep.refs}}))

        # 2c.
        for ep in filter(self.row_filter('U'), self.i_graph.values()):
            if ep.refs[0][ref_idx.ROW] == 'C':
                if 'C' not in self.app_graph or ep.refs[0][ref_idx.INDEX] >= len(self.app_graph['C']):
                    self.status.append(text_token({'E01015': {'u_ep': [*ep[1:3]], 'refs': ep.refs}}))

        # 3a
        for row in filter(self.dst_filter(self.unreferenced_filter()), self.i_graph.values()):
            self.status.append(text_token({'E01001': {'ep_type': ['Destination', 'Source'][row[ep_idx.EP_TYPE]],
                                                      'ref': [row[ep_idx.ROW], row[ep_idx.INDEX]]}}))

        # 3b
        references = [hash_ref(ref, DST_EP) for ep in filter(self.src_filter(), self.i_graph.values()) for ref in ep.refs]
        for dupe, _ in filter(lambda x: x[1] > 1, Counter(references).items()):
            referencing_eps = []
            for ep in filter(self.src_filter(), self.i_graph.values()):
                if dupe in (hash_ref(ref, DST_EP) for ref in ep.refs):
                    referencing_eps.append(ep)
            self.status.append(text_token({'E01018': {'dupe': dupe, 'refs': referencing_eps}}))

        # 4
        for row in filter(lambda x: not validate(x[ep_idx.TYPE]), self.i_graph.values()):
            self.status.append(text_token({'E01002': {'ep_type': ['Destination', 'Source'][row[ep_idx.EP_TYPE]],
                                                      'ref': [row[ep_idx.ROW], row[ep_idx.INDEX]],
                                                      'type_errors': 'Does not exist.'}}))

        # 5
        ref_dict = {k: [] for k in gc_graph.rows}
        ep_dict = deepcopy(ref_dict)
        for row in self.i_graph.values():
            for ref in row[ep_idx.REFERENCED_BY]:
                ref_dict[ref.row].append(ref.idx)
            ep_dict[row[ep_idx.ROW]].append(row[ep_idx.INDEX])
        for k, v in ref_dict.items():
            ep = ep_dict[k]
            if ep:
                if not (min(ep) == 0 and max(ep) == len(set(ep)) - 1):
                    self.status.append(text_token({'E01003': {'row': k, 'indices': sorted(ep)}}))
            if v:
                if not (min(v) == 0 and max(v) == len(set(v)) - 1):
                    _logger.debug(f'{ref_dict}')
                    self.status.append(text_token({'E01004': {'row': k, 'indices': sorted(v)}}))

        # 6
        for row in filter(lambda x: x[ep_idx.ROW] == 'C' and not validate_value(x[ep_idx.VALUE],
                          x[ep_idx.TYPE]), self.i_graph.values()):
            self.status.append(text_token({'E01005': {'ref': [row[ep_idx.ROW], row[ep_idx.INDEX]],
                                                      'value': row[ep_idx.VALUE],
                                                      'type': asstr(row[ep_idx.TYPE])}}))

        # 7
        if self.has_f() != bool(len(list(filter(self.row_filter('P'), self.i_graph.values())))):
            self.status.append(text_token({'E01006': {}}))

        # 8 & 9
        # FIXME: It is not possible to tell from the graph whether this is a codon or not

        # 10
        for row in filter(self.row_filter('I', self.dst_filter()), self.i_graph.values()):
            self.status.append(text_token({'E01007': {'ref': [row[ep_idx.ROW], row[ep_idx.INDEX]]}}))

        # 11
        for row in filter(self.rows_filter(('O', 'P'), self.src_filter()), self.i_graph.values()):
            self.status.append(text_token({'E01008': {'ref': [row[ep_idx.ROW], row[ep_idx.INDEX]]}}))

        # 12
        for row in filter(self.dst_filter(), self.i_graph.values()):
            for ref in row[ep_idx.REFERENCED_BY]:
                try:
                    src = next(filter(self.src_filter(self.ref_filter(ref)), self.i_graph.values()))
                    if not compatible(src[ep_idx.TYPE], row[ep_idx.TYPE]):
                        self.status.append(text_token({'E01009': {'ref1': [src[ep_idx.ROW], src[ep_idx.INDEX]],
                                                                  'type1': asstr(src[ep_idx.TYPE]),
                                                                  'ref2': [row[ep_idx.ROW], row[ep_idx.INDEX]],
                                                                  'type2': asstr(row[ep_idx.TYPE])}}))
                except StopIteration:
                    pass

        # 13a
        for row in filter(self.dst_filter(), self.i_graph.values()):
            for ref in row[ep_idx.REFERENCED_BY]:
                if ref.row not in gc_graph.src_rows[row[ep_idx.ROW]]:
                    self.status.append(text_token({'E01010': {'ref1': [row[ep_idx.ROW], row[ep_idx.INDEX]],
                                                              'ref2': [ref.row, ref.idx]}}))

        # 13b
        for row in filter(self.src_filter(), self.i_graph.values()):
            for ref in row[ep_idx.REFERENCED_BY]:
                if ref.row in gc_graph.src_rows[row[ep_idx.ROW]] or ref.row == row:
                    self.status.append(text_token({'E01017': {'ref1': [row[ep_idx.ROW], row[ep_idx.INDEX]],
                                                              'ref2': [ref.row, ref.idx]}}))

        # 14a
        if self.has_f():
            for row in filter(self.row_filter('B', self.dst_filter()), self.i_graph.values()):
                for ref in filter(lambda x: x[ref_idx.ROW] == 'A', row[ep_idx.REFERENCED_BY]):
                    self.status.append(text_token({'E01011': {'ref1': [row[ep_idx.ROW], row[ep_idx.INDEX]],
                                                              'ref2': [ref.row, ref.idx]}}))

        # 14b
        if self.has_f() and self.has_b():
            for row in filter(self.row_filter('O'), self.i_graph.values()):
                for ref in row[ep_idx.REFERENCED_BY]:
                    if ref.row == 'B':
                        self.status.append(text_token({'E01012': {'ref1': [row[ep_idx.ROW],
                                                                  row[ep_idx.INDEX]], 'ref2': ref}}))

        # 14c
        if self.has_f():
            len_row_p = len(list(filter(self.row_filter('P'), self.i_graph.values())))
            if len_row_p != self.num_outputs():
                self.status.append(text_token({'E01013': {'len_p': len_row_p, 'len_o': self.num_outputs()}}))

        # 14d
        if self.has_f():
            bools = [ep.typ == asint('bool') for ep in filter(self.row_filter('I'), self.i_graph.values())]
            if not bools:
                self.status.append(text_token({'E01016': {}}))

        if _LOG_DEBUG:
            if self.status:
                _logger.debug("Graph internal format:\n{}".format(self))
            for m in self.status:
                _logger.debug(m)
            # Self consistency check.
            str(self)

        return not self.status

    def random_mutation(self):
        """Randomly selects a way to mutate the graph and executes it.

        Mutations are single steps e.g. a disconnection of a source endpoint. The
        reconnection is a repair(). Compound changes are only permitted when
        there is only one possible repair option (excluding undoing the change) e.g.
        adding row 'F' requires that row 'P' must be added however, both rows endpoints
        may be connected many ways.

        Changes are likely to break the graph but they may not. For example,
        disconnecting a source end point will break it but change the type
        of an input source or the value of a constant may not.

        Each random change has the same probability:
            1. Add/remove a source end point.
            2. Add/remove a destination endpoint.
            3. Mutate the type of an endpoint.
            4. Mutate a constant.
            5. Add/remove 'F' (and 'P')

        """
        change_functions = (
            self.random_add_src_ep,
            self.random_remove_src_ep,
            self.random_add_dst_ep,
            self.random_remove_dst_ep
        )
        choice(change_functions)()

    def random_add_src_ep(self):
        """Randomly choose a source row and add an endpoint of unknown type."""
        src_rows = ['I', 'C', 'A']
        if self.has_b():
            src_rows.append('B')
        self.add_src_ep(choice(src_rows))

    def add_src_ep(self, row):
        """Add an endpoint to row of UNKNOWN_EP_TYPE_VALUE."""
        self._add_ep([SRC_EP, row, None, UNKNOWN_EP_TYPE_VALUE, []])
        if row == 'I':
            self.status.append(text_token({'I01000': {}}))
        elif row == 'A':
            self.status.append(text_token({'I01100': {}}))
        elif row == 'B':
            self.status.append(text_token({'I01200': {}}))

    def random_remove_src_ep(self):
        """Randomly choose a source row and randomly remove an endpoint."""
        src_rows = [r for r in gc_graph.src_rows['O'] if r in self.rows[SRC_EP]]
        ep_list = self.unreferenced_filter(self.row_filter(choice(src_rows), self.src_filter()))
        self.remove_src_ep(tuple(choice(ep_list)))

    def remove_src_ep(self, ep_list):
        """Remove a source endpoint."""
        if ep_list:
            ep = ep_list[0]
            ep_row = ep.row
            self._remove_ep(ep)
            if ep_row == 'I':
                self.status.append(text_token({'I01001': {}}))
            elif ep_row == 'A':
                self.status.append(text_token({'I01101': {}}))
            elif ep_row == 'B':
                self.status.append(text_token({'I01201': {}}))
        else:
            self.status.append(text_token({'I01900': {}}))

    def random_add_dst_ep(self):
        """Randomly choose a destination row and add an endpoint of unknown type."""
        dst_rows = ['A', 'O']
        if self.has_b():
            dst_rows.append('B')
        self.add_dst_ep(choice(dst_rows))

    def add_dst_ep(self, row):
        """Add an endpoint to row of UNKNOWN_EP_TYPE_VALUE."""
        self._add_ep([DST_EP, row, None, UNKNOWN_EP_TYPE_VALUE, []])
        if row == 'O':
            self.status.append(text_token({'I01302': {}}))
            if self.has_f():
                self._add_ep([DST_EP, 'P', None, UNKNOWN_EP_TYPE_VALUE, []])
                self.status.append(text_token({'I01402': {}}))
        elif row == 'A':
            self.status.append(text_token({'I01102': {}}))
        elif row == 'B':
            self.status.append(text_token({'I01202': {}}))

    def remove_rows(self, rows):
        """Remove rows from the graph."""
        # FIXME: This does not make sense. Removing a row is a bigger operation than just in the graph
        # Find all endpoints from the rows to delete, collect the endpoints that reference them
        # and delete the row endpoints.
        ref_list = []
        for k in tuple(filter(lambda x: x[0] in rows, self.i_graph.keys())):
            ref_list.extend([hash_ref(ref, not self.i_graph[k][ep_idx.EP_TYPE]) for ref in self.i_graph[k][ep_idx.REFERENCED_BY]])
            if _LOG_DEBUG:
                _logger.debug(f'Deleting endpoint {k}')
            del self.i_graph[k]

        # Update the row endpoint count tracking
        for row in rows:
            if row in self.rows[SRC_EP]:
                del self.rows[SRC_EP][row]
            if row in self.rows[DST_EP]:
                del self.rows[DST_EP][row]

        # Find all the references to deleted rows and delete them
        for ep_hash in ref_list:
            refs = self.i_graph[ep_hash][ep_idx.REFERENCED_BY]
            self.i_graph[ep_hash][ep_idx.REFERENCED_BY] = [ref for ref in refs if ref.row not in rows]
            if _LOG_DEBUG:
                _logger.debug(f'Refactoring endpoint references from {refs} to {self.i_graph[ep_hash][ep_idx.REFERENCED_BY]}')

        # If row A is removed and there is a row B, B becomes A.
        if 'A' in rows and self.has_b() and 'B' not in rows:
            self.i_graph.update({'A' + k[1:]: v for k, v in self.i_graph.items() if k[0] == 'B'})
            for ref in (ref for ep in self.i_graph.values() for ref in ep.refs if ref.row == 'B'):
                ref.row = 'A'
            if 'B' in self.rows[SRC_EP]:
                self.rows[SRC_EP]['A'] = self.rows[SRC_EP]['B']
                del self.rows[SRC_EP]['B']
            if 'B' in self.rows[DST_EP]:
                self.rows[DST_EP]['A'] = self.rows[DST_EP]['B']
                del self.rows[DST_EP]['B']

    def random_remove_dst_ep(self):
        """Randomly choose a destination row and randomly remove an endpoint."""
        dst_rows = ['A', 'O']
        if self.has_b():
            dst_rows.append('B')
        ep_list = self.unreferenced_filter(self.row_filter(choice(dst_rows), self.dst_filter))
        self.remove_dst_ep(tuple(choice(ep_list)))

    def remove_dst_ep(self, ep_list):
        """Remove a destination endpoint.

        Args
        ----
            ep_list (list): A list of destination endpoints. Only the first endpoint
                            in the list will be removed.
        """
        if ep_list:
            ep = ep_list[0]
            ep_row = ep.row
            self._remove_ep(ep)
            if ep_row == 'O':
                self.status.append(text_token({'I01303': {}}))
                if self.has_f():
                    ep.row = 'P'
                    self._remove_ep(ep)
                    self.status.append(text_token({'I01403': {}}))
            elif ep_row == 'A':
                self.status.append(text_token({'I01103': {}}))
            elif ep_row == 'B':
                self.status.append(text_token({'I01203': {}}))
        else:
            self.status.append(text_token({'I01900': {}}))

    def remove_all_connections(self):
        """Remove all connections."""
        for ep in self.i_graph.values():
            ep.refs.clear()

    def random_remove_connection(self, n=1):
        """Randomly choose n connections and remove them.

        n is the number of connections to remove and must be >=0 (0 is
        a no-op). If n is greater than the number of connections all connections are removed.

        Args
        ----
            n (int): Number of connections to remove.

        This is done by selecting all of the connected destination endpoint not in row U and
        randomly sampling n.
        """
        dst_ep_tuple = tuple(filter(self.dst_filter(self.referenced_filter(), False), self.i_graph.values()))
        if _LOG_DEBUG:
            _logger.debug("Selecting connection to remove from destination endpoint tuple: {}".format(dst_ep_tuple))
        if dst_ep_tuple:
            self.remove_connection(sample(dst_ep_tuple, min((len(dst_ep_tuple), n))))

    def remove_connection(self, dst_ep_tuple):
        """Remove connections to all the destination endpoints.

        Args
        ----
            dst_ep_seq (tuple): A list of destination endpoints to disconnect.
        """
        src_ep_tuple = (self.i_graph[hash_ref(dst_ep.refs[0], SRC_EP)] for dst_ep in dst_ep_tuple)
        for src_ep, dst_ep in zip(src_ep_tuple, dst_ep_tuple):
            dst_ep.refs = []
            src_ep.refs.remove([dst_ep.row, dst_ep.idx])

    def random_add_connection(self):
        """Randomly choose two endpoints to connect.

        This is done by first selecting an unconnected destination endpoint then
        randomly (no filtering) choosing a viable source endpoint.
        """
        dst_ep_list = list(filter(self.unreferenced_filter(self.dst_filter()), self.i_graph.values()))
        if _LOG_DEBUG:
            _logger.debug("Selecting connection to add to destination endpoint list: {}".format(dst_ep_list))
        if dst_ep_list:
            self.add_connection([choice(dst_ep_list)])

    def connect_all(self):
        """Connect all unconnected destination endpoints.

        Find all the unreferenced destination endpoints and connect them to a random viable source.
        If there is no viable source endpoint the destination endpoint will remain unconnected.
        """
        dst_ep_list = list(filter(self.unreferenced_filter(self.dst_filter()), self.i_graph.values()))
        for dst_ep in dst_ep_list:
            self.add_connection([dst_ep])

    def add_connection(self, dst_ep_list, src_ep_filter_func=lambda x: True):
        """Add a connection to source from destination specified by src_ep_filter.

        Args
        ----
            dst_ep_list (list): A list of destination endpoints. Only the first endpoint
                in the list that is unconnected will be connected.
            src_ep_filter_func (func): A function that takes an endpoint list as the
                single argument and returns a filtered & sorted endpoint list from which
                one source endpoint will be randomly chosen.
        """
        if dst_ep_list:
            dst_ep = dst_ep_list[0]
            if _LOG_DEBUG:
                _logger.debug("The destination endpoint requiring a connection: {}".format(dst_ep))
            src_ep_list = list(filter(self.src_filter(self.src_row_filter(dst_ep.row,
                                                                          self.type_filter([dst_ep.typ],
                                                                          src_ep_filter_func, exact=False))),
                                      self.i_graph.values()))
            if src_ep_list:
                src_ep = choice(src_ep_list)
                if _LOG_DEBUG:
                    _logger.debug("The source endpoint to make the connection: {}".format(src_ep))
                dst_ep.refs = [src_ep[1:3]]
                src_ep.refs.append(dst_ep[1:3])
                return True
            if _LOG_DEBUG:
                _logger.debug("No viable source endpoints for destination endpoint: {}".format(dst_ep))
        return False

    def stack(self, gB):
        """Stack this graph on top of graph gB.

        Graph gA (self) is stacked on gB to make gC i.e. gC inputs are gA's inputs
        and gC's outputs are gB's outputs:
            1. gC's inputs directly connect to gA's inputs, 1:1 in order
            2. gB's inputs preferentially connect to gA's outputs 1:1
            3. gB's outputs directly connect to gC's outputs, 1:1 in order
            4. Any gA's outputs that are not connected to gB inputs create new gC outputs
            5. Any gBs input that are not connected to gA outputs create new gC inputs

        Stacking only works if there is at least 1 connection from gA's outputs to gB's inputs.

        Args
        ----
        gB (gc_graph): Graph to sit on top of.

        Returns
        -------
        (gc_graph): gC.
        """
        # TODO: Stacking is inserting under row O which changes the output interface
        # that means it cannot be done on a sub-GC - but to what end?

        # Create all the end points
        ep_list = []
        for ep in filter(gB.rows_filter(('I', 'O')), gB.graph.values()):
            row, idx, typ = ep.row, ep.idx, ep.typ
            if row == 'I':
                ep_list.append([False, 'B', idx, typ, []])
            elif row == 'O':
                ep_list.append([True, 'B', idx, typ, [['O', idx]]])
                ep_list.append([False, 'O', idx, typ, [['B', idx]]])

        for ep in filter(self.rows_filter(('I', 'O')), self.i_graph.values()):
            row, idx, typ = ep.row, ep.idx, ep.typ
            if row == 'I':
                ep_list.append([True, 'I', idx, typ, [['A', idx]]])
                ep_list.append([False, 'A', idx, typ, [['I', idx]]])
            elif row == 'O':
                ep_list.append([True, 'A', idx, typ, []])

        # Make a gC gc_graph object
        gC = gc_graph()
        for ep in ep_list:
            gC._add_ep(ep)

        # Preferentially connect A --> B but only 1:1
        gA_gB_connection = False
        for ep in filter(gC.dst_filter(gC.row_filter('B')), gC.graph.values()):
            gA_gB_connection = gA_gB_connection or gC.add_connection([ep], gC.row_filter('A', gC.unreferenced_filter()))

        if gA_gB_connection:
            # Extend O with any remaining A src's
            for ep in tuple(filter(gC.src_filter(gC.row_filter('A', gC.unreferenced_filter())), gC.graph.values())):
                idx = gC.num_outputs()
                gC._add_ep([DST_EP, 'O', idx, ep.typ, [['A', ep.idx]]])
                ep.refs.append(['O', idx])

            # Extend I with any remaining B dst's
            for ep in tuple(filter(gC.dst_filter(gC.row_filter('B', gC.unreferenced_filter())), gC.graph.values())):
                idx = gC.num_inputs()
                gC._add_ep([SRC_EP, 'I', idx, ep.typ, [['B', ep.idx]]])
                ep.refs.append(['I', idx])

            return gC
        return None

    def input_if(self):
        """Return the input interface definition.

        Returns
        -------
        inputs (list(int)): Integers are ep_type_ints in the order defined in the graph.
        """
        eps = (ep for ep in filter(lambda x: x[ep_idx.ROW] == 'I', self.i_graph.values()))
        sorted_eps = sorted(eps, key=lambda x: x[ep_idx.INDEX])
        previous = -1
        inputs = []
        for ep in filter(lambda x: x[ep_idx.INDEX] != previous, sorted_eps):
            previous = ep.idx
            inputs.append(ep.typ)
        return inputs

    def output_if(self):
        """Return the output interface definition.

        Returns
        -------
        outputs (list(int)): Integers are ep_type_ints in the order defined in the graph.
        """
        outputs = sorted((ep for ep in filter(_OUT_FUNC, self.i_graph.values())), key=lambda x: x[ep_idx.INDEX])
        return [ep.typ for ep in outputs]
