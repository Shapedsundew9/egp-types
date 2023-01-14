from logging import DEBUG, NullHandler, getLogger, Logger
from .xgc_validator import xgc_validator_generator, XGC_ENTRY_SCHEMA
from .reference import ref_str

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class _GC(dict):
    """Abstract base class for genetic code (GC) types.

    Validity is in the context of a steady state GC i.e. an INVALID field will not cause
    a validate() failure but the GC will not be stable (valid).

    All derived classes mutate the the supplied dict-like object to make
    it a valid _GC type. The dict is NOT copied.
    """

    _GC_ENTRIES: tuple[str, ...] = ('ref',)
    validator: xgc_validator_generator = xgc_validator_generator({k: XGC_ENTRY_SCHEMA[k] for k in _GC_ENTRIES}, allow_unknow=True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        retval: str = '\t{\n'
        for k, v in sorted(self.items(), key=lambda x: x[0]):
            retval = retval + '\t\t' + f"'{k}'{' ' * (21 - len(k))}: "
            if 'ref' in k and 'refs' not in k:
                retval += ref_str(v)
            else:
                retval += str(v)
            retval += '\n'
        return retval + '\t}'

    def validate(self) -> None:
        """Validate all required key:value pairs are correct."""
        if not self.validator.validate(self):
            raise ValueError(f"Validation FAILED with:\n{self.validator.error_str()}")
