"""_GC is the abstract base class for *GC classes.

*GC classes are dict-like classes. Whilst not actually a Typeddict, validation
restricts the fields that are present in each. Some fields are optional and/or
derived.
*GC classes stack with the following hierarchy:
# _GC   Common abstract base class
# eGC   Embryonic GC - may be unstable
# mGC   Minimum viable GC - must be stable
# gGC   Gene Pool Cache (GPC) GC - all fields required to be defined for the GPC
# xGC   Extended GC - includes transient fields
Each *GC is a superset of the one below.
The goal of the class is performance and storage efficiency. eGC, mGC & gGC derived
from the standard dict class for access performance and flexibility during live
computation. The xGC class which has a highly optimised in memory storage
implementation.
"""
from logging import Logger, NullHandler, getLogger
from typing import LiteralString, Any
from egp_utils.base_validator import base_validator

from .reference import ref_str

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())


class _GC():
    """Abstract base class for genetic code (*GC) types.

    The base class assumes the derived class implements:
        a) items()
        b) validator as a Validator instance.
    """

    _GC_ENTRIES: tuple[LiteralString, ...] = tuple()
    validator: base_validator

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

    @staticmethod
    def new_reference() -> int:
        """Bound to the reference generation function."""
        raise NotImplementedError('Abstract base class.')

    def stablize(self) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Bound to the stabilization function."""
        raise NotImplementedError('Abstract base class.')

