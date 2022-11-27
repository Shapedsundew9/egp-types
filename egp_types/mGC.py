from logging import DEBUG, NullHandler, getLogger
from .xgc_validator import xgc_validator_generator, XGC_ENTRY_SCHEMA
from ._GC import _GC
from .eGC import eGC
from .ep_type import vtype, interface_definition
from .gc_graph import gc_graph


_logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG = _logger.isEnabledFor(DEBUG)


class mGC(_GC):
    """Minimal GC type.

    Minimal GC's have the minimal set of fields with valid values necessary to form a GC.
    A Minimal GC (mGC) has the same fields as an embryonic GC but provides the valid values guarantee.
    """

    _MGC_ENTRIES = (*eGC._EGC_ENTRIES, 'inputs', 'outputs', 'input_types', 'output_types')
    validator = xgc_validator_generator({k: XGC_ENTRY_SCHEMA[k] for k in _MGC_ENTRIES}, allow_unknow=True)

    def __init__(self, gc={}, igraph=gc_graph(), sv=True):
        """Construct.

        gc combined with igraph must be in a steady state.
        if gc['igraph'] exists igraph will be ignored.

        Args
        ----
        gc (a _GC dervived object): GC to ensure is mGC compliant.
        gca_ref (int or None): gca reference.
        gcb_ref (int or None): gcb reference.
        sv (bool): Suppress validation. If True the mGC will not be validated on construction.
        """
        super().__init__(gc)
        self.setdefault('igraph', igraph)
        self.setdefault('gca_ref', self.field_reference('gca'))
        self.setdefault('gcb_ref', self.field_reference('gcb'))
        self.setdefault('generation', 0)
        self.setdefault('ancestor_a_ref', None)
        self.setdefault('ancestor_b_ref', None)
        if 'inputs' not in self:
            inputs = self['igraph'].input_if()
            outputs = self['igraph'].output_if()
            _, self['input_types'], self['inputs'] = interface_definition(inputs, vtype.EP_TYPE_INT)
            _, self['output_types'], self['outputs'] = interface_definition(outputs, vtype.EP_TYPE_INT)

