from egp_types.reference import ref_from_sig, _GL_GC, reference
from random import seed
from random import getrandbits, randint
from itertools import count

# Reproducibly random
seed(100)


def test_ref_from_sig_basic() -> None:
    test_signatures: tuple[bytes, ...] = tuple(bytearray(getrandbits(8) for _ in range(32)) for _ in range(1000))
    for signature in test_signatures:
        assert ref_from_sig(signature) < 0, "MSb not set in GL GC reference!"


def test_ref_from_sig_shift() -> None:
    for _ in range(1000):
        shift: int = randint(0, 192)
        ref: int = getrandbits(63)
        sig: int = ref << shift
        rfs: int = ref_from_sig(sig.to_bytes(32, 'big'), shift)
        assert rfs == (ref - _GL_GC), f"{sig:032x} >> {shift} with GL GC bit set != {rfs:08x}"


def test_reference() -> None:
    counters: dict[int, count] = {}
    # Owner 0 count 0
    assert not reference(0, counters)
    assert reference(0, counters) == 1
    assert reference(0, counters) == 2
    assert reference(1, counters) == 0x100000000
    assert reference(1, counters) == 0x100000001
    assert reference(1, counters) == 0x100000002
    assert reference(0, counters) == 3
    assert reference(0, counters) == 4
    assert reference(1, counters) == 0x100000003
    assert reference(1, counters) == 0x100000004
