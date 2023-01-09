from logging import DEBUG, NullHandler, getLogger
from copy import copy
from .gc_type_tools import is_pgc, _GL_EXCLUDE_COLUMNS
from .xgc_validator import GGC_entry_validator
from .gc_graph import gc_graph
from egp_execution.execution import remove_callable
from .ep_type import vtype, interface_definition
from ._GC import _GC


_logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG = _logger.isEnabledFor(DEBUG)


class GGC(_GC):
    """Gene Pool GC type.

    Gene pool GC types hold a lot of transient data.
    GGC's are stored in the Gene Pool Cache.
    Only 1 instance can exist: Copying or recreating will raise an exception.
    """

    higher_layer_cols = tuple((col for col in filter(lambda x: x[0] == '_', GGC_entry_validator.schema.keys())))

    def __init__(self, gc={}, modified=True, population_uid=None, sv=True):
        """Construct.

        Ensure all fields are defined as required for the Gene Pool.
        If gc has a 'signature' then it may have been pulled from the
        genomic library and already exist in the gene pool cache. If so
        the GGC is not recreated.

        Args
        ----
        gc (a _GC dervived object): GC to ensure is eGC compliant.
        sv (bool): Suppress validation. If True the eGC will not be validated on construction.
        """
        super().__init__(gc)
        assert self['ref'] is not None

        self._sv = sv
        self['modified'] = modified
        self.setdefault('ac_count', 1)
        self.setdefault('cb')

        # FIXME: Not needed if ref is a function of population_uid.
        self.setdefault('population_uid', population_uid)
        _logger.debug(f"self['population_uid']={self['population_uid']}, population_uid={population_uid}")

        self.setdefault('pgc_ref', self.field_reference('pgc'))
        self.setdefault('gca_ref', self.field_reference('gca'))
        self.setdefault('gcb_ref', self.field_reference('gcb'))
        self.setdefault('graph', {})
        self.setdefault('igraph', gc_graph(self['graph']))
        self.setdefault('generation', 0)
        self.setdefault('sms_ref', None)
        # FIXME: I do not recall how far I got with the implementation of these.
        # self.setdefault('effective_pgc_refs', [])
        # self.setdefault('effective_pgc_fitness', [])
        self.setdefault('offspring_count', 0)
        if 'inputs' not in self:
            inputs = self['igraph'].input_if()
            outputs = self['igraph'].output_if()
            _, self['input_types'], self['inputs'] = interface_definition(inputs, vtype.EP_TYPE_INT)
            _, self['output_types'], self['outputs'] = interface_definition(outputs, vtype.EP_TYPE_INT)

        self['num_inputs'] = len(self['inputs'])
        self['num_outputs'] = len(self['outputs'])
        self['callable'] = None

        if _LOG_DEBUG and not sv:
            # Inefficient to recreate GGC's.
            assert not isinstance(gc, GGC)

            # Avoid a copy of GGC which causes issues with __del__() of the 'exec' function.
            gc = dict(self)
            _logger.debug(f'Validating GGC: {self} using dictionary: {gc}')
            _logger.debug(','.join([f'{k}: {type(v)}({v})' for k, v in gc.items()]))
            if not GGC_entry_validator(gc):
                _logger.error(f'GGC invalid:\n{GGC_entry_validator.error_str()}.')
                assert False

    def __del__(self):
        """Make sure the 'exec' function is cleaned up."""
        if _LOG_DEBUG:
            _logger.debug(f"Deleting {self['ref']}.")
        remove_callable(self)

    def __copy__(self):
        """Make sure we do not copy GGCs."""
        assert False, f"Shallow copy of GGC {self['ref']}"

    def __deepcopy__(self):
        """Make sure we do not copy GGCs."""
        assert False, f"Deep copy of GGC {self['ref']}"
