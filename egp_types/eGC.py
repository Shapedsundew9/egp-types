from logging import DEBUG, NullHandler, getLogger
from .xgc_validator import xgc_validator_generator, XGC_ENTRY_SCHEMA
from ._GC import _GC
from .ep_type import vtype, interface_definition
from .gc_graph import gc_graph


_logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG = _logger.isEnabledFor(DEBUG)


class eGC(_GC):
    """Embryonic GC type.

    Embryonic GC's have the minimal set of fields necessary to form a GC but the values
    are not necessarily valid. A Minimal GC (mGC) has the same fields as an
    embryonic GC but provides the valid minimal field values guarantee.
    """

    _EGC_ENTRIES = (
        *_GC._GC_ENTRIES, 'gca_ref', 'gcb_ref', 'ancestor_a_ref', 'ancestor_b_ref',
        'generation', 'graph', 'igraph'
    )
    validator = xgc_validator_generator({k: XGC_ENTRY_SCHEMA[k] for k in _EGC_ENTRIES}, allow_unknow=True)

    def __init__(self, gc={}, inputs=None, outputs=None, vt=vtype.OBJECT, sv=True):
        """Construct.

        NOTE: gc will be modified

        Args
        ----
        gc (a dict-like object): GC to ensure is eGC compliant.
        inputs (iterable(object)): GC inputs. Object is of the type defined by vt.
        outputs (iterable(object)): GC outputs. Object is of the type defined by vt.
        vt (vtype): The interpretation of the object. See vtype definition.
        sv (bool): Suppress validation. If True the eGC will not be validated on construction.
        """
        super().__init__(gc)

        if inputs is not None:
            graph_inputs, self['input_types'], self['inputs'] = interface_definition(inputs, vt)
        else:
            graph_inputs = []
        if outputs is not None:
            graph_outputs, self['output_types'], self['outputs'] = interface_definition(outputs, vt)
        else:
            graph_outputs = []
        self.setdefault('gca_ref', self.field_reference('gca'))
        self.setdefault('gcb_ref', self.field_reference('gcb'))
        self.setdefault('ancestor_a_ref', None)
        self.setdefault('ancestor_b_ref', None)
        self.setdefault('generation', 0)
        self['modified'] = True
        if 'igraph' not in self:
            if 'graph' in self:
                igraph = gc_graph(self['graph'])
                graph_inputs = igraph.input_if()
                graph_outputs = igraph.output_if()
            else:
                igraph = gc_graph()
                igraph.add_inputs(graph_inputs)
                igraph.add_outputs(graph_outputs)
                igraph.normalize()
                self['graph'] = igraph.application_graph()
            self['igraph'] = igraph
        elif 'graph' not in self:
            self['graph'] = self['igraph'].application_graph()
        
        # Validation
        if not sv:
            if not eGC.validator(self):
                _logger.error(f'eGC creation validation falied:\n{eGC.validator.error_str()}')
