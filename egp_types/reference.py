"""Reference definition and tools."""
from itertools import count
from typing import Callable, Literal

_REFERENCE_MASK: Literal[9223372036854775807] = 0x7FFFFFFFFFFFFFFF
_GL_GC: Literal[9223372036854775808] = 0x8000000000000000


# Pretty print for references
_OVER_MAX: int = 1 << 64
_MASK: int = _OVER_MAX - 1
ref_str: Callable[[int], str] = lambda x: 'None' if x is None else f"{((_OVER_MAX + x) & _MASK):016x}"


class ISPUIDOverflowError(Exception):
    """Raised when the ISPUID overflows."""


def isGLGC(ref: int) -> bool:
    """Test if a reference is for a GC loaded from the GL."""
    return bool(ref < 0)


def ref_from_sig(signature: bytes, shift: int = 0) -> int:
    """Create a 64 bit reference from a signature.

    See reference() for significance of bit fields.
    shift can be used to make up to 192 alternate references

    Args
    ----
    signature: 32 element bytes object
    shift: Defines the lowest bit in the signature of the 63 bit reference

    Returns
    -------
    Reference
    """
    high: int = 32 - (shift >> 3)
    mask: int = shift & 7
    if not mask:
        return (int.from_bytes(signature[high - 8:high], byteorder="big") & _REFERENCE_MASK) - _GL_GC

    low: int = high - 9
    return ((int.from_bytes(signature[low:high], byteorder="big") >> mask) & _REFERENCE_MASK) - _GL_GC


def reference(gpspuid: int, counter: count) -> int:
    """Create a unique reference.

    The reference 0x00000000000000000 is reserved and will not be created.

    References have the structure:

    | Bit Field | Name | Description |
    ----------------------------------
    | 63 | GL | Set to 0 for all new references. 1 if reference came from a signature.
    | 62:32 | GPSPUID | Gene Pool Sub-Process UID |
    | 31:0 | ISPUID | Intra-Sub-Process UId |

    Args
    ----
    gpspuid: 32 bit unsigned integer uniquely identifying sub-process in the gene pool scope.

    Returns
    -------
    Signed 64 bit integer
    """
    ispuid: int = next(counter)
    if ispuid == 0x100000000:
        raise ISPUIDOverflowError()
    if not gpspuid and not ispuid:
        ispuid = 1
    return ispuid + ((gpspuid & 0x7FFFFFFF) << 32)


def get_gpspuid(ref: int) -> int:
    """Get the GPSPUID from a reference."""
    return (ref >> 32) & 0x7FFFFFFF


def get_ispuid(ref: int) -> int:
    """Get the ISPUID from a reference."""
    return ref & 0xFFFFFFFF
