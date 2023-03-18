"""Tools for managing genetic code graphs.

Created Date: Sunday, July 19th 2020, 2:56:11 pm
Author: Shapedsundew9

Description: Genetic code graphs define how genetic codes are connected together. The gc_graph_tools module
defines the rules of the connectivity (the "physics") i.e. what is possible to observe or occur.
"""

from collections import Counter
from logging import DEBUG, Logger, NullHandler, getLogger
from math import sqrt
from pprint import pformat
from random import choice, randint, sample
from typing import Any, Iterable, Literal, LiteralString, Sequence

import gi
from bokeh.io import output_file, save
from bokeh.models import (BoxSelectTool, Circle, ColumnDataSource,
                          GraphRenderer, HoverTool, LabelSet, MultiLine,
                          NodesAndLinkedEdges, Range1d, TapTool)
from bokeh.palettes import Category20_20, Greys9
from bokeh.plotting import figure, from_networkx
from cairo import FONT_WEIGHT_BOLD, FontWeight  # pylint: disable=no-name-in-module
from egp_utils.text_token import register_token_code, text_token
from graph_tool import EdgePropertyMap, Graph, VertexPropertyMap
from graph_tool.draw import graph_draw
from networkx import DiGraph, get_node_attributes, spring_layout

from .egp_typing import (CPI, CVI, DST_EP, ROWS, SOURCE_ROWS, SRC_EP,
                         VALID_ROW_SOURCES, ConnectionGraph, DestinationRow,
                         DstEndPoint, DstEndPointReference, Edge, EndPoint,
                         EndPointClass, EndPointHash, EndPointIndex,
                         EndPointReference, EndPointType, GCGraphRows,
                         InternalGraph, PairIdx, Row, SourceRow, SrcEndPoint,
                         SrcEndPointHash, SrcEndPointReference, Vertex,
                         isConnectionPair, isConstantPair)
from .ep_type import (REAL_EP_TYPE_VALUES, asint, asstr, compatible,
                      import_str, type_str, validate)
from .xgc_validator import graph_validator

# Needed to prevent something pulling in GtK 4.0 and graph_tool complaining.
gi.require_version('Gtk', '3.0')


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# NetworkX & Bokeh parameters
_NX_NODE_RADIUS: Literal[30] = 30
_NX_NODE_FONT: Literal['courier'] = 'courier'
_NX_HOVER_TOOLTIPS: list[tuple[str, str]] = [("Type", "@type"), ("Value", "@value"), ("EP Type", "@ep_type")]
_NX_ROW_EDGE_ATTR: dict[str, str] = {
    'line': Greys9[4],
    'select': Greys9[0],
    'hover': Greys9[0]
}
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
for _, _v in _NX_ROW_NODE_ATTR.items():
    _v['font'] = _NX_NODE_FONT


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
for _, _v in _GT_ROW_NODE_ATTR.items():
    _v['size'] = _GT_NODE_DIAMETER
    _v['shape'] = _GT_NODE_SHAPE
    _v['font_size'] = _GT_NODE_FONT_SIZE
    _v['font_weight'] = _GT_NODE_FONT_WEIGHT

_GT_EDGE_PEN_WIDTH: Literal[4] = 4
_GT_EDGE_MARKER_SIZE: Literal[24] = 24


register_token_code('E01000', 'A graph must have at least one output.')
register_token_code('E01001', '{ep_hash} endpoint is not connected to anything.')
register_token_code('E01002', '{ep_hash} endpoint does not have a valid type: {type_errors}.')
register_token_code('E01003', '{cls_str} row {row} does not have contiguous indices starting at 0: {indices}.')
register_token_code('E01004', 'The {cls_str} row {row} endpoint count ({row_count}) != i_graph count ({i_count})')
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
register_token_code('E01019', 'Endpoint {ep_hash} references {ref_hash} but it does not exist.')
register_token_code('E01020', 'Endpoint {ep_hash} references {ref_hash} but {ref_hash} does not reference it back.')

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
def validate_value(value_str, ep_type_int) -> bool:
    """Validate the executable string is a valid ep_type value.

    Args
    ----
        value_str (str): As string that when executed as the RHS of an assignment returns a value of ep_type
        ep_type_int (int): An Endpoint Type Definition (see ref).

    Returns
    -------
        bool: True if valid else False
    """
    tstr: str = type_str(ep_type_int)
    try:
        eval(tstr)  # pylint: disable=eval-used
    except NameError:
        if _LOG_DEBUG:
            _logger.debug(f'Importing {tstr}.')
        exec(import_str(ep_type_int))  # pylint: disable=exec-used

    if _LOG_DEBUG:
        _logger.debug(f'retval = isinstance({value_str}, {tstr})')
    try:
        retval: bool = eval(f'isinstance({value_str}, {tstr})')  # pylint: disable=eval-used
    except (NameError, SyntaxError):
        return False
    return retval


# TODO: Consider caching calculated results.
class gc_graph():
    """Manipulating Genetic Code Graphs."""
    __slots__: tuple[LiteralString, ...] = ('i_graph', 'rows', 'app_graph', 'status', 'has_f')
    i_graph: InternalGraph
    rows: GCGraphRows
    app_graph: Any
    status: Any
    has_f: bool

    def __init__(self, c_graph: ConnectionGraph | None = None, i_graph: InternalGraph | None = None) -> None:

        nc_graph: ConnectionGraph = {} if c_graph is None else c_graph
        self.i_graph = i_graph if i_graph is not None else self._convert_to_internal(nc_graph)
        self.rows = (dict(Counter([ep.row for ep in self.i_graph.dst_filter()])),
                     dict(Counter([ep.row for ep in self.i_graph.src_filter()])))
        self.has_f = 'F' in self.rows[DST_EP]

    def __repr__(self) -> str:
        """Print the graph in row order sources then destinations in index order."""
        # NOTE: This function is used in determining the signature of a GC.
        str_list: list[str] = []
        for row in ROWS:
            for ep_class in (False, True):
                row_dict: dict[str, EndPoint] = {k: v for k, v in self.i_graph.items() if v.cls == ep_class and v.row == row}
                str_list.extend(["'" + k + "': " + str(v) for k, v in sorted(row_dict.items(), key=lambda x: x[1].idx)])
        return ', '.join(str_list)

    def _convert_to_internal(self, c_graph: ConnectionGraph) -> InternalGraph:
        """Convert graph to internal format.

        The internal format allows quicker searching for parameters by type, endpoint type etc.
        It maintains bi-directional references for quick manipulation.
        Types are stored in integer format for efficiency.
        """
        i_graph: InternalGraph = InternalGraph()
        for connection_graph_pair in c_graph.items():
            if isConnectionPair(connection_graph_pair):
                row: DestinationRow = connection_graph_pair[PairIdx.ROW.value]
                for index, c_point in enumerate(connection_graph_pair[PairIdx.VALUES.value]):
                    cp_row: SourceRow = c_point[CPI.ROW.value]
                    cp_idx: EndPointIndex = c_point[CPI.IDX.value]
                    cp_typ: EndPointType = c_point[CPI.TYP.value]
                    dst_ep: DstEndPoint = DstEndPoint(row, index, cp_typ, refs=[SrcEndPointReference(cp_row, cp_idx)])
                    i_graph[dst_ep.key()] = dst_ep
                    src_ep_hash: SrcEndPointHash = dst_ep.refs[0].key()
                    if src_ep_hash in i_graph:
                        i_graph[src_ep_hash].refs.append(DstEndPointReference(row, index))
                    elif cp_row != 'C':
                        refs: list[DstEndPointReference] = [DstEndPointReference(row, index)] if row != 'U' else []
                        i_graph[src_ep_hash] = SrcEndPoint(cp_row, cp_idx, cp_typ, refs=refs)
            elif isConstantPair(connection_graph_pair):
                for index, c_point in enumerate(connection_graph_pair[PairIdx.VALUES.value]):
                    src_ep: EndPoint = SrcEndPoint('C', index, c_point[CVI.TYP.value], val=c_point[CVI.VAL.value])
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
        for ep in sorted(self.i_graph.dst_filter(), key=lambda x: x.idx):
            row: DestinationRow = ep.row
            graph.setdefault(row, []).append((ep.refs[0].row, ep.refs[0].idx, ep.typ))
        for ep in sorted(self.i_graph.row_filter('C'), key=lambda x: x.idx):
            if 'C' not in graph:
                graph['C'] = []
            graph.setdefault('C', []).append((ep.typ, ep.val))
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
        for ep in self.i_graph.dst_filter():
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
        bk_graph.node_renderer.glyph = Circle(line_color='line', size='size', fill_color="fill")  # type: ignore
        bk_graph.node_renderer.selection_glyph = Circle(line_color='line', size='size', fill_color="select")  # type: ignore
        bk_graph.node_renderer.hover_glyph = Circle(line_color='line', size='size', fill_color="hover")  # type: ignore
        bk_graph.edge_renderer.glyph = MultiLine(line_color="line", line_alpha=0.8, line_width=2)  # type: ignore
        bk_graph.edge_renderer.selection_glyph = MultiLine(line_color="select", line_width=3)  # type: ignore
        bk_graph.edge_renderer.hover_glyph = MultiLine(line_color="hover", line_width=3)  # type: ignore
        bk_graph.selection_policy = NodesAndLinkedEdges()  # type: ignore
        bk_graph.inspection_policy = NodesAndLinkedEdges()  # type: ignore
        plot.renderers.append(bk_graph)  # type: ignore

        x_y: tuple[tuple[float, ...], tuple[float, ...]] = tuple(
            zip(*bk_graph.layout_provider.graph_layout.values()))  # pylint: disable=no-member, # type: ignore
        node_labels: dict[str, str] = get_node_attributes(nx_graph, 'text')
        label_x_offsets: dict[str, float] = get_node_attributes(nx_graph, 'x_offset')
        label_y_offsets: dict[str, float] = get_node_attributes(nx_graph, 'y_offset')
        label_font_sizes: dict[str, str] = get_node_attributes(nx_graph, 'font_size')
        label_font: dict[str, str] = get_node_attributes(nx_graph, 'font')
        source: ColumnDataSource = ColumnDataSource({
            'x': x_y[0],
            'y': x_y[1],
            'text': list(node_labels.values()),
            'x_offset': list(label_x_offsets.values()),
            'y_offset': list(label_y_offsets.values()),
            'font_size': list(label_font_sizes.values()),
            'font': list(label_font.values())
        })
        labels: LabelSet = LabelSet(x='x', y='y', text='text',
                                    source=source, text_font_size='font_size', x_offset='x_offset', y_offset='y_offset',
                                    text_font='font', text_font_style='bold', text_color='black')
        plot.renderers.append(labels)  # type: ignore
        output_file(f"{path}.html", title="Erasmus GP GC Internal Graph")
        save(plot)

    def gt_graph(self) -> tuple[Graph, dict[str, VertexPropertyMap], dict[str, EdgePropertyMap]]:
        """Create a graph_tool graph treating rows as nodes.

        graph_tool is used because its drawing capabilities allow for multiple edges between nodes (unlike Bokeh)
        though it has much more limited interactions.

        Returns
        -------
            (Graph): A graph_tool Graph object.
            (dict): Dict of vertex properties.
            (dict): Dict of edge properties.
        """
        graph: Graph = Graph()
        node_p: dict[str, VertexPropertyMap] = {
            'text': graph.new_vertex_property('string'),
            'shape': graph.new_vertex_property('string'),
            'fill_color': graph.new_vertex_property('vector<float>'),
            'size': graph.new_vertex_property('int'),
            'font_size': graph.new_vertex_property('int'),
            'font_weight': graph.new_vertex_property('int')
        }
        edge_p: dict[str, EdgePropertyMap] = {
            'pen_width': graph.new_edge_property('int'),
            'marker_size': graph.new_edge_property('int')
        }

        gtg: dict[Row, Vertex] = {}
        for row in ROWS:
            dst_list: tuple[DstEndPoint, ...] = tuple(self.i_graph.dst_row_filter(row))
            src_list: tuple[SrcEndPoint, ...] = tuple(self.i_graph.src_row_filter(row))
            size: int = max((len(dst_list), len(src_list)))
            if size:
                node: Vertex = graph.add_vertex()  # type: ignore
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to gt_graph node: {row}")
                for k, v in _GT_ROW_NODE_ATTR[row].items():
                    node_p[k][node] = v
                node_p['size'][node] = round(node_p['size'][node] * sqrt(size))
                node_p['font_size'][node] = round(node_p['font_size'][node] * sqrt(size))
                gtg[row] = node
            for ep in dst_list:
                dst_row: DestinationRow = ep.row
                src_row: SourceRow = ep.refs[0].row
                if _LOG_DEBUG:
                    _logger.debug(f"Adding to gt_graph edge: {src_row}->{dst_row}")
                edge: Edge = graph.add_edge(gtg[src_row], gtg[dst_row])  # type: ignore
                edge_p['pen_width'][edge] = _GT_EDGE_PEN_WIDTH
                edge_p['marker_size'][edge] = _GT_EDGE_MARKER_SIZE
        return graph, node_p, edge_p

    def gt_draw(self, path="./gt_graph", size=(1600, 900)) -> None:
        """Draw the graph_tool row node graph.

        Args
        ----
            path (str): folder plus base file name of the output image. '.png' will be appended.
            size ((int, int)): Tuple of x, y output image dimensions.
        """
        graph_properties: tuple[Graph, dict[str, VertexPropertyMap], dict[str, EdgePropertyMap]] = self.gt_graph()
        node_p: dict[str, VertexPropertyMap] = graph_properties[1]
        edge_p: dict[str, EdgePropertyMap] = graph_properties[2]
        graph_draw(graph_properties[0], vertex_text=node_p['text'], vertex_shape=node_p['shape'],
                   vertex_fill_color=node_p['fill_color'], vertex_size=node_p['size'],
                   vertex_font_weight=node_p['font_weight'], vertex_font_size=node_p['font_size'],
                   edge_pen_width=edge_p['pen_width'], edge_marker_size=edge_p['marker_size'],
                   output=path + ".png", output_size=size)

    def draw(self, path='./graph', size=(1600, 900)) -> None:
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

    def add_input(self, ep_type: int | None = None) -> None:
        """Create and append an unconnected row I endpoint.

        Args
        ----
        ep_type: ep_type in integer format. If None a random real ep_type is chosen.
        """
        if ep_type is None:
            self._add_ep(SrcEndPoint('I', self.rows[SRC_EP].get('I', 0), choice(REAL_EP_TYPE_VALUES)))
        else:
            self._add_ep(SrcEndPoint('I', self.rows[SRC_EP].get('I', 0), ep_type))

    def remove_input(self, idx: int | None = None) -> None:
        """Remove input idx.

        No-op if there are no inputs.

        Args
        ----
        idx: Index of input to remove. If None a random index is chosen.
        """
        num_inputs: int = self.rows[SRC_EP].get('I', 0)
        if num_inputs:
            nidx: int = randint(0, num_inputs - 1) if idx is None else idx
            ep_ref: SrcEndPointReference = SrcEndPointReference('I', nidx)
            if _LOG_DEBUG:
                _logger.debug(f"Removing input {ep_ref}.")
            ep: SrcEndPoint = self.i_graph[ep_ref.key()]  # type: ignore
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[ref.key()].refs.remove(ep_ref)

            # Only re-index row I if it was not the last endpoint that was removed (optimisation)
            if nidx != num_inputs - 1:
                self.reindex_row('I')

    def add_output(self, ep_type: int | None = None) -> None:
        """Create and append an unconnected row O endpoint.

        Args
        ----
        ep_type: ep_type in integer format. If None a random real ep_type is chosen.
        """
        nep_type: int = choice(REAL_EP_TYPE_VALUES) if ep_type is None else ep_type
        o_index: int = self.rows[DST_EP].get('O', 0)
        self._add_ep(DstEndPoint('O', o_index, nep_type))
        if self.has_f:
            self._add_ep(DstEndPoint('P', o_index, nep_type))

    def remove_output(self, idx: int | None = None) -> None:
        """Remove output idx.

        No-op if there are no outputs.

        Args
        ----
        idx: Index of output to remove. If None a random index is chosen.
        """
        num_outputs: int = self.rows[DST_EP].get('O', 0)
        if num_outputs:
            nidx: int = randint(0, num_outputs - 1) if idx is None else idx
            ep_ref: DstEndPointReference = DstEndPointReference('O', nidx)
            if _LOG_DEBUG:
                _logger.debug(f"Removing output {ep_ref}.")
            ep: DstEndPoint = self.i_graph[ep_ref.key()]  # type: ignore
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[ref.key()].refs.remove(ep_ref)

            # If F exists then must deal with P
            if self.has_f:
                ep_ref: DstEndPointReference = DstEndPointReference('P', nidx)
                if _LOG_DEBUG:
                    _logger.debug(f"Removing output {ep_ref}.")
            ep: DstEndPoint = self.i_graph[ep_ref.key()]  # type: ignore
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[ref.key()].refs.remove(ep_ref)

            # Only re-index row O if it was not the last endpoint that was removed (optimisation)
            if idx != num_outputs - 1:
                self.reindex_row('O')
                if self.has_f:
                    self.reindex_row('P')

    def remove_constant(self, idx=None) -> None:
        """Remove constant idx.

        No-op if there are no constants.

        Args
        ----
        idx: Index of constant to remove. If None a random index is chosen.
        """
        num_constants: int = self.rows[SRC_EP].get('C', 0)
        if num_constants:
            nidx: int = randint(0, num_constants - 1) if idx is None else idx
            ep_ref: SrcEndPointReference = SrcEndPointReference('C', nidx)
            if _LOG_DEBUG:
                _logger.debug(f"Removing constant {ep_ref}.")
            ep: SrcEndPoint = self.i_graph[ep_ref.key()]  # type: ignore
            self._remove_ep(ep, False)
            for ref in ep.refs:
                self.i_graph[ref.key()].refs.remove(ep_ref)

            # Only re-index row I if it was not the last endpoint that was removed (optimisation)
            if nidx != num_constants - 1:
                self.reindex_row('C')

    def add_inputs(self, inputs: Iterable[int]) -> None:
        """Create and add unconnected row I endpoints.

        Will replace any existing endpoints with the same index.

        Args
        ----
        inputs: ep_types in integer format.
        """
        for index, i in enumerate(inputs):
            self._add_ep(SrcEndPoint('I', index, i))

    def add_outputs(self, outputs: Iterable[int]) -> None:
        """Create and add unconnected row O endpoints.

        Will replace any existing endpoints with the same index.

        Args
        ----
        outputs: ep_types in integer format.
        """
        for index, i in enumerate(outputs):
            self._add_ep(DstEndPoint('O', index, i))

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

    def reindex_row(self, row: Literal['I', 'C', 'P', 'U', 'O']) -> None:
        """Re-index row.

        If end points have been removed from a row the row will need
        reindexing so the indicies are contiguous (starting at 0).

        Rows A & B cannot be reindexed as their interfaces are bound to
        a GC definition.

        Args
        ----
        row: One of 'ICPUO'
        """
        # Map the indices to a contiguous integer sequence starting at 0
        r_map: dict[int, int] = {idx: i for i, idx in enumerate((ep.idx for ep in self.i_graph.row_filter(row)))}
        # For each row select all the endpoints and iterate through the references to them
        # For each reference update: Find the reverse reference and update it with the new index
        # Finally update the index in the endpoint
        # TODO: Do we need to re-create this filter?
        for ep in tuple(self.i_graph.row_filter(row)):
            if _LOG_DEBUG:
                _logger.debug(f"References to re-index: {ep.refs}")
            for ref in ep.refs:
                for refd in self.i_graph[ref.force_key(not ep.cls)].refs:
                    if refd.row == row and refd.idx == ep.idx:
                        refd.idx = r_map[ep.idx]
            del self.i_graph[ep.key()]
            ep.idx = r_map[ep.idx]
            self.i_graph[ep.key()] = ep

    def normalize(self) -> bool:
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
        for ep in tuple(self.i_graph.row_filter('U')):
            self._remove_ep(ep, check=False)
        for ep in self.i_graph.values():
            victims = reversed(tuple(idx for idx, ref in enumerate(ep.refs) if ref.row == 'U'))
            for idx in victims:
                del ep.refs[idx]

        # 1 Connect all destinations to existing sources if possible
        self.connect_all()

        # 4 Reference all unconnected sources in row 'U'
        # First remove all existing row U endpoints
        # Then any references to them
        # Finally add the new unreferenced connections.
        for idx, ep in enumerate(self.i_graph.src_unref_filter()):
            self._add_ep(DstEndPoint('U', idx, ep.typ, refs=[SrcEndPointReference(ep.row, ep.idx)]))
            ep.refs = [DstEndPointReference('U', idx)]

        # 5 self.app_graph is regenerated
        self.app_graph = self.connection_graph()

        # 6 Check a valid steady state has been achieved
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
        return not tuple(self.i_graph.dst_unref_filter())

    def validate(self) -> bool:  # noqa: C901
        """Check if the graph is valid.

        The graph should be in a steady state before calling.

        This function is not intended to be fast.
        Genetic code graphs MUST obey the following rules:
            1. All connections are referenced at source and destination.
            2. All sources are connected or referenced by the unconnected 'U' row.
            3a. All destinations are connected.
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

        Args
        ----
        Set to True if the graph is for a codon genetic code.

        Returns
        -------
        True if the graph is valid else False.
        If False is returned details of the errors found are in the errors member.
        """
        self.status = []

        # 1.
        for ep in self.i_graph.values():
            for ref in ep.refs:
                ref_hash: EndPointHash = ref.force_key(not ep.cls)
                if ref_hash not in self.i_graph:
                    self.status.append(text_token({'E1019': {'ep_hash': ep.key(), 'ref_hash': ref_hash}}))
                elif EndPointReference(ep.row, ep.idx) not in self.i_graph[ref_hash].refs:
                    self.status.append(text_token({'E1020': {'ep_hash': ep.key(), 'ref_hash': ref_hash}}))

        # 2.
        for ep in self.i_graph.src_unref_filter():
            self.status.append(text_token({'E01001': {'ep_hash': ep.key()}}))

        # 3a.
        for ep in self.i_graph.dst_unref_filter():
            self.status.append(text_token({'E01001': {'ep_hash': ep.key()}}))

        # 3b.
        for ep in self.i_graph.dst_filter():
            if len(ep.refs) > 1:
                self.status.append(text_token({'E01018': {'dupe': ep.key(), 'refs': ep.refs}}))

        # 4
        for ep in filter(lambda x: not validate(x.typ), self.i_graph.values()):
            self.status.append(text_token({'E01002': {'ep_hash': ep.key(), 'type_errors': 'Does not exist.'}}))

        # 5
        for row in ROWS:
            for cls_row, cls_str in ((self.i_graph.src_row_filter(row), 'Src'), (self.i_graph.dst_row_filter(row), 'Dst')):
                indices: list[int] = sorted((ep.idx for ep in cls_row))
                if [idx for idx in indices if idx not in range(indices[-1] + 1)]:
                    self.status.append(text_token({'E1003': {'cls_str': cls_str, 'row': row, 'indices': indices}}))

        # 6
        for ep in filter(lambda x: validate_value(x.val, x.typ), self.i_graph.row_filter('C')):
            self.status.append(text_token({'E01005': {'ref': ep.key(), 'value': ep.val, 'type': asstr(ep.typ)}}))

        # 7
        if self.has_f != 'P' in self.rows[DST_EP]:
            self.status.append(text_token({'E01006': {}}))

        # 8
        for row in ROWS:
            for count, cls in ((self.i_graph.num_eps(row, SRC_EP), SRC_EP), (self.i_graph.num_eps(row, DST_EP), DST_EP)):
                if self.rows[cls][row] != count:
                    self.status.append(text_token({'E1004': {
                        'cls_str': ('source', 'desintation')[cls],
                        'row': row,
                        'row_count': self.rows[cls][row],
                        'i_count': count
                    }}))

        #  & 9
        # FIXME: It is not possible to tell from the graph whether this is a codon or not

        # 10
        for ep in self.i_graph.row_filter('I'):
            if ep.cls != SRC_EP:
                self.status.append(text_token({'E01007': {'ref': ep.key()}}))

        # 11
        for ep in self.i_graph.rows_filter(('O', 'P')):
            if ep.cls != DST_EP:
                self.status.append(text_token({'E01008': {'ref': ep.key()}}))

        # 12
        for dst_ep in self.i_graph.dst_filter():
            for ref in dst_ep.refs:
                src_ep: EndPoint = self.i_graph[ref.key()]
                if not compatible(src_ep.typ, dst_ep.typ):
                    self.status.append(text_token({'E01009': {'ref1': src_ep.key(),
                                                              'type1': asstr(src_ep.typ),
                                                              'ref2': dst_ep.key(),
                                                              'type2': asstr(dst_ep.typ)}}))

        # 13a
        for ep in self.i_graph.dst_filter():
            for ref in ep.refs:
                if ref.row not in VALID_ROW_SOURCES[self.has_f][ep.row]:
                    self.status.append(text_token({'E01010': {'ref1': ep.key(), 'ref2': ref.key()}}))

        # 13b
        for ep in self.i_graph.src_filter():
            for ref in ep.refs:
                if ref.row in SOURCE_ROWS or ref.row == ep.row:
                    self.status.append(text_token({'E01017': {'ref1': ep.key(), 'ref2': ref.key()}}))

        # 14a
        if self.has_f:
            len_p: int = self.i_graph.num_eps('P', DST_EP)
            len_o: int = self.i_graph.num_eps('O', DST_EP)
            if len_p != len_o:
                self.status.append(text_token({'E01013': {'len_p': len_p, 'len_o': len_o}}))

        # 14b
        if self.has_f:
            if not [ep.typ == asint('bool') for ep in self.i_graph.row_filter('I')]:
                self.status.append(text_token({'E01016': {}}))

        if _LOG_DEBUG:
            if self.status:
                _logger.debug(f'Graph internal format:\n{self}')
            for status in self.status:
                _logger.debug(status)

        return not self.status

    def remove_all_connections(self) -> None:
        """Remove all connections."""
        for ep in self.i_graph.values():
            ep.refs.clear()

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
        dst_ep_tuple = tuple(self.i_graph.dst_ref_filter())
        if _LOG_DEBUG:
            _logger.debug(f'Selecting connection to remove from destination endpoint tuple: {dst_ep_tuple}')
        if dst_ep_tuple:
            self.remove_connection(sample(dst_ep_tuple, min((len(dst_ep_tuple), num))))

    def remove_connection(self, dst_ep_iter: Iterable[DstEndPoint]) -> None:
        """Remove connections to the specified destination endpoints.

        Args
        ----
        dst_ep_seq: An iterable of destination endpoints to disconnect.
        """
        for dst_ep in dst_ep_iter:
            self.i_graph[dst_ep.refs[0].key()].refs.remove(DstEndPointReference(dst_ep.row, dst_ep.idx))

    def random_add_connection(self) -> None:
        """Randomly choose two endpoints to connect.

        This is done by first selecting an unconnected destination endpoint then
        randomly (no filtering) choosing a viable source endpoint.
        """
        dst_ep_tuple = tuple(self.i_graph.dst_unref_filter())
        if _LOG_DEBUG:
            _logger.debug(f'Selecting connection to add to destination endpoint list: {dst_ep_tuple}')
        if dst_ep_tuple:
            self.add_connection(choice(dst_ep_tuple))

    def connect_all(self) -> None:
        """Connect all unconnected destination endpoints.

        Find all the unreferenced destination endpoints and connect them to a random viable source.
        If there is no viable source endpoint the destination endpoint will remain unconnected.
        """
        for dst_ep in self.i_graph.dst_unref_filter():
            self.add_connection(dst_ep)

    def add_connection(self, dst_ep: DstEndPoint,
                       allowed_rows: Sequence[SourceRow] = SOURCE_ROWS,
                       unreferenced: bool = False) -> bool:
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
            _logger.debug(f'The destination endpoint requiring a connection: {dst_ep}')

        filter_func = self.i_graph.src_unref_filter if unreferenced else self.i_graph.src_filter
        eligible_rows = tuple(row for row in VALID_ROW_SOURCES[self.has_f] if row in allowed_rows)
        src_eps = tuple(src_ep for src_ep in filter_func() if src_ep.row in eligible_rows)
        if src_eps:
            src_ep: SrcEndPoint = choice(src_eps)
            if _LOG_DEBUG:
                _logger.debug(f'The source endpoint to make the connection: {src_ep}')
            dst_ep.refs = [src_ep.as_ref()]
            src_ep.refs.append(dst_ep.as_ref())
            return True
        if _LOG_DEBUG:
            _logger.debug(f'No viable source endpoints for destination endpoint: {dst_ep}')
        return False

    def input_if(self) -> list[int]:
        """Return the input interface definition.

        Returns
        -------
        A list of integers which are ep_type_ints in the order defined in the graph.
        """
        return [ep.typ for ep in sorted(self.i_graph.row_filter('I'), key=lambda x: x.idx)]

    def output_if(self) -> list[int]:
        """Return the output interface definition.

        Returns
        -------
        A list of integers which are ep_type_ints in the order defined in the graph.
        """
        return [ep.typ for ep in sorted(self.i_graph.row_filter('O'), key=lambda x: x.idx)]
