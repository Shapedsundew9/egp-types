"""Reference definition and tools."""
from typing import Literal, Callable
from itertools import count


_REFERENCE_MASK: Literal[9223372036854775807] = 0x7FFFFFFFFFFFFFFF
_GL_GC: Literal[9223372036854775808] = 0x8000000000000000 # type: ignore
_MAX_OWNER: Literal[2147483647] = 0x7FFFFFFF


# Pretty print for references
_OVER_MAX: int = 1 << 64
_MASK: int = _OVER_MAX - 1
ref_str: Callable[[int], str] = lambda x: 'None' if x is None else f"{((_OVER_MAX + x) & _MASK):016x}"


def ref_from_sig(signature:bytes, shift:int = 0) -> int:
    """Create a 63 bit reference from a signature.

    See reference() for significance of bit fields.
    shift can be used to make up to 193 alternate references
    
    Args
    ----
    signature: 32 element bytes object
    shift: Defines the lowest bit in the signature of the 63 bit reference

    Returns
    -------
    Reference    
    """
    if not shift:
        return int.from_bytes(signature[:8], "little") | _GL_GC 

    low: int = shift >> 3
    high: int = low + 9
    window: int = _REFERENCE_MASK << (shift & 0x3)
    return ((int.from_bytes(signature[low:high], "little") & window) >> shift) | _GL_GC
    

def reference(owner:int, counters:dict[int, count]) -> int:
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
    owner: 32 bit unsigned integer uniquely identifying the counter to be used.

    Returns
    -------
    Signed 64 bit integer reference.
    """
    if owner not in counters:
        assert owner < _MAX_OWNER, "Owner index out of range."
        counters[owner] = count(2**32)
    return (next(counters[owner]) + (owner << 32))
