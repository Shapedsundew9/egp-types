"""The embryonic GC (eGC) class."""
from logging import DEBUG, Logger, NullHandler, getLogger
from typing import Any, LiteralString, Iterable, Sequence, Callable, NoReturn

from .ep_type import interface_definition, vtype
from .gc_graph import gc_graph
from .xgc_validator import XGC_ENTRY_SCHEMA, xgc_validator_generator
from .reference import ref_str

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


def not_implemented_exception() -> NoReturn:
    """Bound to the reference generation function."""
    raise NotImplementedError('Abstract base class.')


class eGC(dict):
    """Embryonic GC type.

    Embryonic GC's have the minimal set of fields necessary to form a GC but the
    graph is not necessarily valid.
    """

    _EGC_ENTRIES: tuple[LiteralString, ...] = (
        'gca_ref', 'gcb_ref', 'ancestor_a_ref', 'ancestor_b_ref',
        'generation', 'gc_graph'
    )
    validator: xgc_validator_generator = xgc_validator_generator({k: XGC_ENTRY_SCHEMA[k] for k in _EGC_ENTRIES}, allow_unknown=True)
    new_reference: Callable[[], NoReturn | int] = not_implemented_exception

    def __init__(
            self,
            gc: dict | None = None,
            inputs: Iterable[Any] | None = None,
            outputs: Iterable[Any] | None = None,
            vt: vtype = vtype.OBJECT) -> None:
        """Construct.

        NOTE: gc will be modified

        Args
        ----
        gc: GC to ensure is eGC compliant.
        inputs: GC inputs. Object is of the type defined by vt.
        outputs: GC outputs. Object is of the type defined by vt.
        vt: The interpretation of the object. See vtype definition.
        """
        if gc is not None:
            super().__init__(gc)
        else:
            super().__init__()

        graph_inputs: Sequence[int] | None = None
        graph_outputs: Sequence[int] | None = None
        if inputs is not None:
            iid_types: tuple[tuple[int, ...], list[int], bytes] = interface_definition(inputs, vt)
            graph_inputs = iid_types[0]
            self['input_types'] = iid_types[1]
            self['inputs'] = iid_types[2]

        if outputs is not None:
            oid_types: tuple[tuple[int, ...], list[int], bytes] = interface_definition(outputs, vt)
            graph_outputs = oid_types[0]
            self['output_types'] = oid_types[1]
            self['outputs'] = oid_types[2]

        if 'ref' not in self:
            self['ref'] = eGC.new_reference()

        if 'gc_graph' not in self:
            if 'graph' in self:
                gcgraph: gc_graph = gc_graph(self['graph'])
            else:
                gcgraph = gc_graph()
                if graph_inputs is not None:
                    gcgraph.add_inputs(graph_inputs)
                if graph_outputs is not None:
                    gcgraph.add_outputs(graph_outputs)
                gcgraph.normalize()
            self['gc_graph'] = gcgraph

        if _LOG_DEBUG:
            if not eGC.validator.validate(self):
                _logger.error(f'eGC creation validation failed:\n{eGC.validator.error_str()}')

    def __repr__(self) -> str:
        """Pretty print."""
        retval: str = '\t{\n'
        for k, v in sorted(self.items(), key=lambda x: x[0]):  # type: ignore
            retval = retval + '\t\t' + f"'{k}'{' ' * (21 - len(k))}: "
            if 'ref' in k and 'refs' not in k and v is not None:
                retval += ref_str(v)
            else:
                retval += str(v)
            retval += '\n'
        return retval + '\t}'

    def validate(self) -> None:
        """Validate all required key:value pairs are correct.

        Validation is an expensive operation and should only be done for debugging.
        Where possible values are checked for consistency.
        """
        if not self.validator.validate(self):
            raise ValueError(f"Validation FAILED with:\n{self.validator.error_str()}")


def set_reference_generator(func: Callable[[], int]) -> None:
    """Define the reference generator for all eGC's."""
    eGC.new_reference = func
