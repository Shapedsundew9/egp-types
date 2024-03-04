"""Test the interface module."""
from pytest import raises
from egp_types.interface import interface, empty_interface, src_interface, dst_interface


def test_instanciation() -> None:
    """Test the instanciation of all interfaces."""
    interface([])
    empty_interface()
    src_interface([])
    dst_interface([])


def test_empty_interface() -> None:
    """Test the empty interface."""
    empty_interface()
    # Modifying an empty interface
    with raises(AssertionError):
        empty_interface().append(None)
    with raises(AssertionError):
        empty_interface().extend([])
    with raises(AssertionError):
        empty_interface().insert(0, None)
    with raises(AssertionError):
        empty_interface()[0] = [2, 3]


def test_interface_assertions() -> None:
    """Test the assertions for an interface."""
    # Not all valid EndPointTypes
    test_interface = interface([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    with raises(ValueError):
        test_interface.assertions()
    # Too many endpoints
    test_interface = interface([2] * 257)
    with raises(ValueError):
        test_interface.assertions()
