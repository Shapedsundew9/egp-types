"""Reference definition and tools."""
from itertools import count
from typing import Callable, Literal

_REFERENCE_MASK: Literal[9223372036854775807] = 0x7FFFFFFFFFFFFFFF
_GL_GC: Literal[9223372036854775808] = 0x8000000000000000


# Pretty print for references
_OVER_MAX: int = 1 << 64
_MASK: int = _OVER_MAX - 1
ref_str: Callable[[int], str] = lambda x: 'None' if x is None else f"{((_OVER_MAX + x) & _MASK):016x}"


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


def reference(owner_id: int, counter: count) -> int:
    """Create a unique reference.

    References have the structure:

    | Bit Field | Name | Description |
    ----------------------------------
    | 63 | GL | 0: Not in the GL, 1: In the GL |
    | 62:0 | TS | When GL = 1: TS = signature[62:0] |
    | 62:32 | OW | When GL = 0: Owner UID |
    | 31:0 | IX | When GL = 0: UID in the owner scope |

    Args
    ----
    owner_id: 31 bit unsigned integer uniquely identifying the counter to be used.

    Returns
    -------
    Signed 64 bit integer reference where the MSb is 0
    """
    return next(counter) + (owner_id << 32)
