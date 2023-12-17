"""Test reference module."""

from itertools import count
from random import getrandbits, randint, seed

from egp_types.reference import _GL_GC, ref_from_sig, reference

# Reproducibly random
seed(100)


def test_ref_from_sig_basic() -> None:
    """Test references from signatures with no shift."""
    test_signatures: tuple[bytes, ...] = tuple(bytearray(getrandbits(8) for _ in range(32)) for _ in range(1000))
    for signature in test_signatures:
        assert ref_from_sig(signature) < 0, "MSb not set in GL GC reference!"


def test_ref_from_sig_shift() -> None:
    """Test references from signatures with a shift. Shift is used in the (unlikely) event of a collision."""
    for _ in range(1000):
        shift: int = randint(0, 192)
        ref: int = getrandbits(63)
        sig: int = ref << shift
        rfs: int = ref_from_sig(sig.to_bytes(32, "big"), shift)
        assert rfs == (ref - _GL_GC), f"{sig:032x} >> {shift} with GL GC bit set != {rfs:08x}"
