from logging import DEBUG, NullHandler, getLogger
from .xgc_validator import xgc_validator_generator, XGC_ENTRY_SCHEMA
from .gc_type_tools import reference, ref_str, ref_from_sig

_logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG = _logger.isEnabledFor(DEBUG)


class _GC(dict):
    """Abstract base class for genetic code (GC) types.

    Validity is in the context of a steady state GC i.e. an INVALID field will not cause
    a validate() failure but the GC will not be stable (valid).

    All derived classes mutate the the supplied dict-like object to make
    it a valid _GC type. The dict is NOT copied.
    """

    _GC_ENTRIES = ('ref',)
    validator = xgc_validator_generator({k: XGC_ENTRY_SCHEMA[k] for k in _GC_ENTRIES}, allow_unknow=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'ref' not in self:
            self['ref'] = self.field_reference('signature', next_ref=True, **kwargs)

    def __repr__(self):
        retval = '\t{\n'
        for k, v in sorted(self.items(), key=lambda x: x[0]):
            retval = retval + '\t\t' + f"'{k}'{' ' * (21 - len(k))}: "
            if 'ref' in k and not 'refs' in k:
                retval += ref_str(v)
            else:
                retval += str(v)
            retval += '\n'
        return retval + '\t}'

    def field_reference(self, field, next_ref=False, **kwargs):
        """Make a reference from the first 8 bytes of the signature if it exists."""
        if field not in self:
            if next_ref:
                return reference(**kwargs)
            return None
        elif self[field] is not None:
            return ref_from_sig(self[field], **kwargs)
        return None

    @classmethod
    def set_next_reference(cls, func):
        """Set the next_reference() method for all GC types.

        The next_reference() class method returns a valid reference to assign
        to an arbitary GC.

        Args
        ----
        func (callable): Function signature: int func(**kwargs) where int is a signed 64 bit value.
        """
        _GC.next_reference = func

    @classmethod
    def set_ref_from_sig(cls, func):
        """Set the ref_from_sig() method for all GC types.

        The ref_from_sig() class method returns a reproducible reference from a signature.

        Args
        ----
        func (callable): Function signature: int func(bytes[32], **kwargs) where int is a signed 64 bit value.
        """
        _GC.ref_from_sig = func

    def validate(self):
        """Validate all required key:value pairs are correct."""
        if not self.validator.validate(self):
            raise ValueError(f"Validation FAILED with:\n{self.validator.error_str()}")
