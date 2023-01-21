from logging import DEBUG, NullHandler, getLogger, Logger
from .xgc_validator import xgc_validator_generator, XGC_ENTRY_SCHEMA
from .eGC import eGC
from .ep_type import vtype, interface_definition
from typing import LiteralString, Iterable


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class mGC(eGC):
    """Minimal GC type.

    Minimal GC's have the minimal set of fields with valid values necessary to form a GC.
    mGC's must be stable.
    """

    _MGC_ENTRIES: tuple[LiteralString, ...] = (*eGC._EGC_ENTRIES, 'inputs', 'outputs', 'input_types', 'output_types')
    validator: xgc_validator_generator = xgc_validator_generator({k: XGC_ENTRY_SCHEMA[k] for k in _MGC_ENTRIES}, allow_unknow=True)

    def __init__(self, gc: dict | eGC) -> None:
        super().__init__(gc)

        if 'inputs' not in self:
            inputs: Iterable[int]= self['igraph'].input_if()
            iid_types: tuple[tuple[int, ...], list[int], bytes] = interface_definition(inputs, vtype.EP_TYPE_INT)
            self['input_types'] = iid_types[1]
            self['inputs'] = iid_types[2]

        if 'outputs' not in self:
            outputs: Iterable[int] = self['igraph'].output_if()
            oid_types: tuple[tuple[int, ...], list[int], bytes] = interface_definition(outputs, vtype.EP_TYPE_INT)
            self['output_types'] = oid_types[1]
            self['outputs'] = oid_types[2]

        if not self['igraph'].is_stable():
            self.stablize()
