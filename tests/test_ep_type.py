"""Validation of ep_type."""

from logging import NullHandler, getLogger, Logger

import pytest

from egp_types.eGC import eGC
from egp_types.ep_type import (EP_TYPE_VALUES, INVALID_EP_TYPE_NAME,
                               INVALID_EP_TYPE_VALUE, UNKNOWN_EP_TYPE_NAME,
                               UNKNOWN_EP_TYPE_VALUE, asint, asstr, compatible,
                               import_str, instance_str, type_str, validate,
                               vtype)
from egp_types.xGC import xGC

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
eGC.new_reference = lambda: 1


@pytest.mark.parametrize("type_object, valid",
                         (
                             (int, True),
                             (str, True),
                             (object, False),
                             (eGC, True),
                             (xGC, True)
                         )
                         )
def test_validate_type_objects(type_object, valid) -> None:
    """Confirm validation of type_objects is correct."""
    assert validate(type_object, vtype.TYPE_OBJECT) == valid


@pytest.mark.parametrize("obj, valid",
                         (
                             (8, True),
                             ("Test", True),
                             ([], False),
                             (eGC(), True),
                             (xGC, False),
                             ({}, False)
                         )
                         )
def test_validate_objects(obj, valid) -> None:
    """Confirm validation of objects is correct."""
    assert validate(obj, vtype.OBJECT) == valid


@pytest.mark.parametrize("string, valid",
                         (
                             ("8", True),
                             ("str(8)", True),
                             ("egp_types_eGC_eGC()", True),
                             ("{}", False)
                         )
                         )
def test_validate_ep_type_str_instances(string, valid) -> None:
    """Confirm validation of EP type names is correct."""
    assert validate(string, vtype.INSTANCE_STR) == valid


@pytest.mark.parametrize("value, valid",
                         (
                             (2, True),
                             (5, True),
                             (-32766, False),  # Reserved for testing
                             (-1, True),
                             (INVALID_EP_TYPE_VALUE, False),
                             (UNKNOWN_EP_TYPE_VALUE, True)
                         )
                         )
def test_validate_ep_type_values(value, valid) -> None:
    """Confirm validation of EP type values is correct."""
    assert validate(value) == valid


@pytest.mark.parametrize("string, valid",
                         (
                             ("builtins_int", True),
                             ("builtins_str", True),
                             ("invalid", False),  # Reserved for testing
                             ("egp_types_eGC_eGC", True),
                             (INVALID_EP_TYPE_NAME, False),
                             (UNKNOWN_EP_TYPE_NAME, True)
                         )
                         )
def test_validate_ep_type_names(string, valid) -> None:
    """Confirm validation of EP type values is correct."""
    assert validate(string, vtype.EP_TYPE_STR) == valid


@pytest.mark.parametrize("type_object, ep_type_int",
                         (
                             (int, 2),
                             (str, 5),
                             (object, INVALID_EP_TYPE_VALUE),
                             (eGC, -1),
                             (xGC, -2)
                         )
                         )
def test_asint_type_objects(type_object, ep_type_int) -> None:
    """Confirm asint() of type_objects is correct."""
    assert asint(type_object, vtype.TYPE_OBJECT) == ep_type_int


@pytest.mark.parametrize("obj, ep_type_int",
                         (
                             (8, 2),
                             ("Test", 5),
                             ([], INVALID_EP_TYPE_VALUE),
                             (eGC(), -1),
                             (xGC, INVALID_EP_TYPE_VALUE),
                             ({}, INVALID_EP_TYPE_VALUE)
                         )
                         )
def test_asint_objects(obj, ep_type_int) -> None:
    """Confirm asint() of objects is correct."""
    assert asint(obj, vtype.OBJECT) == ep_type_int


@pytest.mark.parametrize("string, ep_type_int",
                         (
                             ("8", 2),
                             ("str(8)", 5),
                             ("bytes()", INVALID_EP_TYPE_VALUE),
                             ("invalid()", INVALID_EP_TYPE_VALUE),
                             ("egp_types_eGC_eGC()", -1),
                             ("{}", INVALID_EP_TYPE_VALUE)
                         )
                         )
def test_asint_ep_type_str_instances(string, ep_type_int) -> None:
    """Confirm asint() of str instances is correct."""
    assert asint(string, vtype.INSTANCE_STR) == ep_type_int


@pytest.mark.parametrize("string, ep_type_int",
                         (
                             ("builtins_int", 2),
                             ("builtins_str", 5),
                             ("invalid", INVALID_EP_TYPE_VALUE),  # Reserved for testing
                             ("egp_types_eGC_eGC", -1),
                             (INVALID_EP_TYPE_NAME, INVALID_EP_TYPE_VALUE),
                             (UNKNOWN_EP_TYPE_NAME, UNKNOWN_EP_TYPE_VALUE)
                         )
                         )
def test_asint_ep_type_names(string, ep_type_int) -> None:
    """Confirm asint() of EP type names is correct."""
    assert asint(string, vtype.EP_TYPE_STR) == ep_type_int


@pytest.mark.parametrize("type_object, ep_type_str",
                         (
                             (int, "builtins_int"),
                             (str, "builtins_str"),
                             (object, INVALID_EP_TYPE_NAME),
                             (eGC, "egp_types_eGC_eGC"),
                             (xGC, "egp_types_xGC_xGC")
                         )
                         )
def test_asstr_type_objects(type_object, ep_type_str) -> None:
    """Confirm asstr() of type_objects is correct."""
    assert asstr(type_object, vtype.TYPE_OBJECT) == ep_type_str


@pytest.mark.parametrize("obj, ep_type_str",
                         (
                             (8, "builtins_int"),
                             ("Test", "builtins_str"),
                             ([], INVALID_EP_TYPE_NAME),
                             (eGC(), "egp_types.gc_type_eGC"),
                             (xGC, INVALID_EP_TYPE_NAME),
                             ({}, INVALID_EP_TYPE_NAME)
                         )
                         )
def test_asstr_objects(obj, ep_type_str) -> None:
    """Confirm asstr() of objects is correct."""
    assert asstr(obj, vtype.OBJECT) == ep_type_str


@pytest.mark.parametrize("string, ep_type_str",
                         (
                             ("8", "builtins_int"),
                             ("str(8)", "builtins_str"),
                             ("bytes()", INVALID_EP_TYPE_NAME),
                             ("invalid()", INVALID_EP_TYPE_NAME),
                             ("egp_types_eGC_eGC()", "egp_types_eGC_eGC"),
                             ("{}", INVALID_EP_TYPE_NAME)
                         )
                         )
def test_asstr_ep_type_str_instances(string, ep_type_str) -> None:
    """Confirm asstr() of str instances is correct."""
    assert asstr(string, vtype.INSTANCE_STR) == ep_type_str


@pytest.mark.parametrize("value, ep_type_str",
                         (
                             (2, "builtins_int"),
                             (5, "builtins_str"),
                             (-32766, INVALID_EP_TYPE_NAME),  # Reserved for testing
                             (-1, "egp_types_eGC_eGC"),
                             (INVALID_EP_TYPE_VALUE, INVALID_EP_TYPE_NAME),
                             (UNKNOWN_EP_TYPE_VALUE, UNKNOWN_EP_TYPE_NAME)
                         )
                         )
def test_asstr_ep_type_values(value, ep_type_str) -> None:
    """Confirm asstr() of EP type names is correct."""
    assert asstr(value) == ep_type_str


def test_asstr_ep_type_str() -> None:
    """Confirm asstr() of EP type names strings is correct."""
    assert asstr("builtins_int", vtype.EP_TYPE_STR) == "builtins_int"


def test_import_str() -> None:
    """Check 'None' is returned in at least some cases."""
    assert 'None' in (import_str(eptv) for eptv in EP_TYPE_VALUES)


def test_compatible() -> None:
    """Trivial test for the moment."""
    assert compatible(2, 2)


@pytest.mark.parametrize("ep_type_int, string",
                         (
                             (2, "int"),
                             (5, "str"),
                             (-1, "egp_types_eGC_eGC")
                         )
                         )
def test_type_str(ep_type_int, string) -> None:
    """Confirm type_str() works correctly."""
    assert type_str(ep_type_int) == string


@pytest.mark.parametrize("ep_type_int", EP_TYPE_VALUES)
def test_instance_str(ep_type_int) -> None:
    """Confirm all types can be instanciated."""
    # FIXME: -3 id gGC which is excluded as it has moved to egp_population and wouldcause a circular import
    if ep_type_int not in (INVALID_EP_TYPE_VALUE, UNKNOWN_EP_TYPE_VALUE):
        exec(import_str(ep_type_int))
        eval(instance_str(ep_type_int))
