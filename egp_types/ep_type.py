"""Manages endpoint type interactions.

Endpoint types are identified by a signed 16-bit value or
a fully qualified name.

Erasmus GP types have values < 0.
An invalid ep type has the value -32768
NoneType == 0
All other types values are > 0
"""


from enum import IntEnum
from hashlib import blake2b
from json import load
from logging import Logger, NullHandler, getLogger, DEBUG
from os.path import dirname, join
from typing import Any, Iterable, Literal

from .egp_typing import (
    EndPointTypeLookup,
    EndPointTypeLookupFile,
    isInstanciationValue,
    InstanciationType,
)

_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Load type data
with open(join(dirname(__file__), "data/ep_types.json"), "r", encoding="utf-8") as file_ptr:
    data: EndPointTypeLookupFile = load(file_ptr)
ep_type_lookup: EndPointTypeLookup = {"v2n": {}, "n2v": {}, "instanciation": {}}
ep_type_lookup["v2n"] = {int(k): v for k, v in data["v2n"].items()}
ep_type_lookup["n2v"] = {k: int(v) for k, v in data["n2v"].items()}
ep_type_lookup["instanciation"] = {int(k): v for k, v in data["instanciation"].items() if isInstanciationValue(v)}


_EGP_SPECIAL_TYPE_LIMIT: Literal[-32767] = -32767
_EGP_PHYSICAL_TYPE_LIMIT: Literal[-32369] = -32369
_EGP_REAL_TYPE_LIMIT: Literal[0] = 0
_EGP_TYPE_LIMIT: Literal[32769] = 32769


def _special_type_filter(v) -> bool:
    return _EGP_SPECIAL_TYPE_LIMIT <= v < _EGP_PHYSICAL_TYPE_LIMIT


def _physical_type_filter(v) -> bool:
    return _EGP_PHYSICAL_TYPE_LIMIT <= v < _EGP_REAL_TYPE_LIMIT


def _real_type_filter(v) -> bool:
    return _EGP_REAL_TYPE_LIMIT <= v < _EGP_TYPE_LIMIT


SPECIAL_EP_TYPE_VALUES: tuple[int, ...] = tuple((v for v in filter(_special_type_filter, ep_type_lookup["v2n"])))
PHYSICAL_EP_TYPE_VALUES: tuple[int, ...] = tuple((v for v in filter(_physical_type_filter, ep_type_lookup["v2n"])))
REAL_EP_TYPE_VALUES: tuple[int, ...] = tuple((v for v in filter(_real_type_filter, ep_type_lookup["v2n"])))
_EP_TYPE_VALUES: tuple[int, ...] = (*PHYSICAL_EP_TYPE_VALUES, *REAL_EP_TYPE_VALUES)
MIN_EP_TYPE_VALUE: int = min(_EP_TYPE_VALUES)
MAX_EP_TYPE_VALUE: int = max(_EP_TYPE_VALUES)
assert len(set(_EP_TYPE_VALUES)) == len(_EP_TYPE_VALUES), "Duplicate end point types detected!"
assert max(_EP_TYPE_VALUES) - min(_EP_TYPE_VALUES) == len(_EP_TYPE_VALUES) - 1, "End point types must be contiguous!"

_logger.info(f"{len(SPECIAL_EP_TYPE_VALUES)} special endpoint types identified.")
_logger.info(f"{len(PHYSICAL_EP_TYPE_VALUES)} physical endpoint types identified.")
_logger.info(f"{len(REAL_EP_TYPE_VALUES)} real endpoint types identified.")

INVALID_EP_TYPE_NAME: Literal["egp_invalid_type"] = "egp_invalid_type"
INVALID_EP_TYPE_VALUE: Literal[-32768] = -32768
UNKNOWN_EP_TYPE_NAME: Literal["egp_unknown_type"] = "egp_unknown_type"
UNKNOWN_EP_TYPE_VALUE: Literal[-32767] = -32767

ep_type_lookup["n2v"][INVALID_EP_TYPE_NAME] = INVALID_EP_TYPE_VALUE
ep_type_lookup["v2n"][INVALID_EP_TYPE_VALUE] = INVALID_EP_TYPE_NAME
ep_type_lookup["instanciation"][INVALID_EP_TYPE_VALUE] = (
    None,
    None,
    None,
    None,
    False,
    "INVALID",
)
ep_type_lookup["n2v"][UNKNOWN_EP_TYPE_NAME] = UNKNOWN_EP_TYPE_VALUE
ep_type_lookup["v2n"][UNKNOWN_EP_TYPE_VALUE] = UNKNOWN_EP_TYPE_NAME
ep_type_lookup["instanciation"][UNKNOWN_EP_TYPE_VALUE] = (
    None,
    None,
    None,
    None,
    False,
    "INVALID",
)


class inst(IntEnum):
    """EP type 'instanciation' value list index."""

    PACKAGE = 0  # (str) package name
    VERSION = 1  # (str) package version number
    MODULE = 2  # (str) module name
    NAME = 3  # (str) object name
    PARAM = 4  # (bool or None)
    DEFAULT = 5  # (str) a default value


class vtype(IntEnum):
    """Validation type to use in validate().

    An objects EP type is determined by how the object is interpreted. There are
    5 possible interpretations:
        vtype.EP_TYPE_INT: object is an int and represents an EP type.
        vtype.EP_TYPE_STR: object is a str and represents an EP type.
        vtype.INSTANCE_STR: object is a valid EP type name str.
        vtype.OBJECT: object is a valid EP type object
        vtype.TYPE_OBJECT: object is a type object of the object EP type.
    """

    EP_TYPE_INT = 0
    EP_TYPE_STR = 1
    INSTANCE_STR = 2
    OBJECT = 3
    TYPE_OBJECT = 4


def object_name(i11n: InstanciationType) -> str:
    """Return the imported object name."""
    if i11n[inst.PACKAGE] is None:
        return str(i11n[inst.NAME])
    if i11n[inst.MODULE] is None:
        return "_".join((str(i11n[inst.PACKAGE]), str(i11n[inst.NAME])))
    return "_".join((str(i11n[inst.PACKAGE]), str(i11n[inst.MODULE]), str(i11n[inst.NAME])))


def import_str(ep_type_i: int) -> str:
    """Return the import string for ep_type_int.

    Args
    ----
    ep_type_i: A valid ep_type value.

    Returns
    -------
    The import e.g. 'from numpy import float32 as numpy_float32'
    """
    # FIXME: This needs to become arbitary module depth & consider name collisions.
    i11n: InstanciationType = ep_type_lookup["instanciation"][ep_type_i]
    if i11n[inst.PACKAGE] is None:
        return "None"
    if i11n[inst.MODULE] is None:
        source: str = str(i11n[inst.PACKAGE])
    else:
        source: str = str(i11n[inst.PACKAGE]) + "." + str(i11n[inst.MODULE])
    return f"from {source} import {i11n[inst.NAME]} as {object_name(i11n)}"


# If a type does not exist on this system remove it (all instances will be treated as INVALID)
# NOTE: This would cause a circular dependency with gc_type if GC types were not filtered out
# We can assume GC types will be defined for the contexts they are used.
def func1(i11n) -> bool:
    """Filter function."""
    return i11n[1][inst.PACKAGE] is not None and i11n[1][inst.PACKAGE] != "egp_types"


for _ep_type_int, instn in tuple(filter(func1, ep_type_lookup["instanciation"].items())):
    try:
        exec(import_str(_ep_type_int))  # pylint: disable=exec-used
    except ModuleNotFoundError:
        _logger.warning(f"Module '{instn[inst.MODULE]}' was not found. '{instn[inst.NAME]}' will be treated as an INVALID type.")
        del ep_type_lookup["n2v"][ep_type_lookup["v2n"][_ep_type_int]]
        del ep_type_lookup["instanciation"][_ep_type_int]
        del ep_type_lookup["v2n"][_ep_type_int]
    else:
        _logger.info(import_str(_ep_type_int))


def func2(i11n) -> bool:
    """Filter function."""
    return i11n[inst.PACKAGE] is not None and i11n[inst.PACKAGE] == "egp_types"


_GC_TYPE_NAMES: list[str] = []
for i in tuple(filter(func2, ep_type_lookup["instanciation"].values())):
    _GC_TYPE_NAMES.append(object_name(i))

# Must be defined after the imports
EP_TYPE_NAMES: set[str] = set(ep_type_lookup["n2v"].keys())
EP_TYPE_VALUES: set[int] = set(ep_type_lookup["v2n"].keys())
# Remove the special types
EP_TYPE_VALUES_TUPLE: tuple[int, ...] = tuple(sorted(EP_TYPE_VALUES)[2:])


def validate(obj: Any, value_t: vtype = vtype.EP_TYPE_INT) -> bool:
    """Validate an object as an EP type.

    NOTE: GC types e.g. eGC, mGC etc. cannot be instance strings as they would require
    a circular import. However, since GC types are under the full control of EGP there
    should be no need to try and introspect an instance string for a GC type.

    Args
    ----
    obj: See description above.
    value_t: The interpretation of the object. See vtype definition.:

    Returns
    -------
    True if the type is defined else false.
    """
    if value_t == vtype.TYPE_OBJECT:
        return fully_qualified_name(obj()) in EP_TYPE_NAMES
    if value_t == vtype.OBJECT:
        return fully_qualified_name(obj) in EP_TYPE_NAMES
    if value_t == vtype.INSTANCE_STR:
        try:
            name: str = fully_qualified_name(eval(obj))  # pylint: disable=eval-used
        except NameError:
            # If it looks like a GC type instanciation assume it is OK.
            return any(x + "(" in obj for x in _GC_TYPE_NAMES)
        return name in EP_TYPE_NAMES
    if value_t == vtype.EP_TYPE_STR:
        return obj != INVALID_EP_TYPE_NAME and obj in EP_TYPE_NAMES
    return obj != INVALID_EP_TYPE_VALUE and obj in EP_TYPE_VALUES


def asint(obj: Any, vault_t: vtype = vtype.EP_TYPE_STR) -> int:
    """Return the EP type value for an object.

    NOTE: GC types e.g. eGC, mGC etc. cannot be instance strings as they would require
    a circular import. However, since GC types are under the full control of EGP there
    should be no need to try and introspect an instance string for a GC type.

    Args
    ----
    obj: See description above.
    vault_t: The interpretation of the object. See vtype definition.:

    Returns
    -------
    The EP type of the object (may be egp.invalid_type)
    """
    if vault_t == vtype.TYPE_OBJECT:
        return ep_type_lookup["n2v"].get(fully_qualified_name(obj()), INVALID_EP_TYPE_VALUE)
    if vault_t == vtype.OBJECT:
        return ep_type_lookup["n2v"].get(fully_qualified_name(obj), INVALID_EP_TYPE_VALUE)
    if vault_t == vtype.INSTANCE_STR:
        try:
            ep_type_name: str = fully_qualified_name(eval(obj))  # pylint: disable=eval-used
        except NameError:
            # If it looks like a GC type instanciation assume it is OK.
            ep_type_name = INVALID_EP_TYPE_NAME
            for type_name in _GC_TYPE_NAMES:
                if type_name + "(" in obj:
                    ep_type_name = type_name
                    break
        return ep_type_lookup["n2v"].get(ep_type_name, INVALID_EP_TYPE_VALUE)
    if vault_t == vtype.EP_TYPE_STR:
        return ep_type_lookup["n2v"].get(obj, INVALID_EP_TYPE_VALUE)
    return obj


def asstr(obj: Any, value_t: vtype = vtype.EP_TYPE_INT) -> str:
    """Return the EP type string for an object.

    NOTE: GC types e.g. eGC, mGC etc. cannot be instance strings as they would require
    a circular import. However, since GC types are under the full control of EGP there
    should be no need to try and introspect an instance string for a GC type.

    Args
    ----
    obj: See description above.
    value_t: The interpretation of the object. See vtype definition.


    Returns
    -------
    The EP type of the object (may be egp.invalid_type)
    """
    if value_t == vtype.TYPE_OBJECT:
        ep_type_name: str = fully_qualified_name(obj())
        return ep_type_name if ep_type_name in EP_TYPE_NAMES else INVALID_EP_TYPE_NAME
    if value_t == vtype.OBJECT:
        ep_type_name = fully_qualified_name(obj)
        return ep_type_name if ep_type_name in EP_TYPE_NAMES else INVALID_EP_TYPE_NAME
    if value_t == vtype.INSTANCE_STR:
        try:
            ep_type_name = fully_qualified_name(eval(obj))  # pylint: disable=eval-used
        except NameError:
            # If it looks like a GC type instanciation assume it is OK.
            for type_name in _GC_TYPE_NAMES:
                if type_name + "(" in obj:
                    return type_name
            return INVALID_EP_TYPE_NAME
        return ep_type_name if ep_type_name in EP_TYPE_NAMES else INVALID_EP_TYPE_NAME
    if value_t == vtype.EP_TYPE_INT:
        return ep_type_lookup["v2n"].get(obj, INVALID_EP_TYPE_NAME)
    return obj


def fully_qualified_name(obj: Any) -> str:
    """Return the fully qualified type name for obj.

    Args
    ----
    obj: Any object

    Returns
    -------
    Fully qualified type name.
    """
    return obj.__class__.__module__.replace(".", "_") + "_" + obj.__class__.__qualname__


def compatible(a_type: int | str, b_type: int | str) -> bool:
    """If EP type a is compatible with gc type b return True else False.

    a and b must be of the same type.

    TODO: Define what compatible means. For now it means 'exactly the same type'.

    Args
    ----
    a: A valid ep_type value or name.
    b: A valid ep_type value or name.

    Returns
    -------
    True if a and b are compatible.
    """
    return a_type == b_type


def type_str(ep_type_i: int) -> str:
    """Return the type string for ep_type_int.

    Args
    ----
    ep_type_i: A valid ep_type value.

    Returns
    -------
    The type string e.g. 'int' or 'str'
    """
    i11n: InstanciationType = ep_type_lookup["instanciation"][ep_type_i]
    return object_name(i11n)


def instance_str(ep_type_i: int, param_str: str = "") -> str:
    """Return the instanciation string for ep_type_int.

    Args
    ----
    ep_type_i: A valid ep_type value.
    param_str: A string to be used as instanciation parameters.

    Returns
    -------
    The instanciation e.g. numpy_float32(<param_str>)
    """
    inst_str: str = type_str(ep_type_i)
    if ep_type_lookup["instanciation"][ep_type_i][inst.PARAM]:
        inst_str += f"({param_str})"
    return inst_str


def interface_definition(xputs: Iterable[Any], value_t: vtype = vtype.TYPE_OBJECT) -> tuple[tuple[int, ...], list[int], bytes]:
    """Create an interface definition from xputs.

    Used to define the inputs or outputs of a GC from an iterable
    of types, objects or EP definitions.

    Args
    ----
    xputs: Object is of the type defined by vt.
    value_t: The interpretation of the object. See definition of vtype.

    Returns
    -------
    A list of the xputs as EP type in value format, a list of the EP types in xputs in value format in ascending order and a list of
        indexes into it in the order of xputs.
    """
    xput_eps: tuple[int, ...] = tuple((asint(x, value_t) for x in xputs))
    xput_types: list[int] = sorted(set(xput_eps))
    return xput_eps, xput_types, bytes([xput_types.index(x) for x in xput_eps])


def unordered_interface_hash(input_eps: Iterable[int], output_eps: Iterable[int]) -> int:
    """Create a 64-bit hash of the population interface definition.

    The interface hash is order agnostic i.e.

    (float, int, float) has the same hash as (float, float, int) has
    the same hash as (int, float, float).

    Args
    ----
    input_eps: Iterable of input EP types.
    output_eps: Iterable of output EP types.

    Returns
    -------
    64 bit hash as a signed 64 bit int.
    """
    ihash: blake2b = blake2b(digest_size=8)
    for inpt in sorted(input_eps):
        ihash.update(inpt.to_bytes(2, "big"))
    for outpt in sorted(output_eps):
        ihash.update(outpt.to_bytes(2, "big"))
    ihash_val: int = int.from_bytes(ihash.digest(), "big")
    return (0x7FFFFFFFFFFFFFFF & ihash_val) - (ihash_val & (1 << 63))


def ordered_interface_hash(
    input_types: Iterable[int],
    output_types: Iterable[int],
    inputs: bytes,
    outputs: bytes,
) -> int:
    """Create a 64-bit hash of the population interface definition.

    The interface hash is specific to the order and type in the inputs
    and outputs. This is important in population individuals.

    Args
    ----
    input_types: Iterable of input EP types in ascending order.
    output_types: Iterable of output EP types in ascending order.
    inputs: Indices into input_types for the input parameters.
    outputs: Indices into output_types for the input parameters.

    Returns
    -------
    64 bit hash as a signed 64 bit int.
    """
    ihash: blake2b = blake2b(digest_size=8)
    for inpt in input_types:
        ihash.update(inpt.to_bytes(2, "big"))
    for outpt in sorted(output_types):
        ihash.update(outpt.to_bytes(2, "big"))
    ihash.update(inputs)
    ihash.update(outputs)
    ihash_val: int = int.from_bytes(ihash.digest(), "big")
    return (0x7FFFFFFFFFFFFFFF & ihash_val) - (ihash_val & (1 << 63))


def validate_value(value_str: str, ep_type_int: int) -> bool:
    """Validate the executable string is a valid ep_type value.

    Args
    ----
    value_str: As string that when executed as the RHS of an assignment returns a value of ep_type
    ep_type_int: An Endpoint Type Definition (see ref).

    Returns
    -------
    True if valid else False
    """
    # Is it even a valid end point type value?
    if not validate(ep_type_int):
        return False

    # If it is try to instanciate the string representation
    tstr: str = type_str(ep_type_int)
    try:
        eval(tstr)  # pylint: disable=eval-used
    except NameError:
        execution_str = import_str(ep_type_int)
        if _LOG_DEBUG:
            _logger.debug(f"Import execution string: {execution_str}.")
        exec(execution_str)  # pylint: disable=exec-used

    # None is special
    if value_str == "None" and ep_type_int == ep_type_lookup["n2v"]["None"]:
        return True

    try:
        retval: bool = eval(f"isinstance({value_str}, {tstr})")  # pylint: disable=eval-used
    except (NameError, SyntaxError):
        if _LOG_DEBUG:
            try:
                typ: str = eval(f"type({value_str})")  # pylint: disable=eval-used
            except (NameError, SyntaxError):
                _logger.debug(f"isinstance({value_str}, {tstr}) is False. {value_str} is not a valid object.")
            else:
                _logger.debug(f"isinstance({value_str}, {tstr}) is False. {value_str} is of type {typ}")
        return False
    if _LOG_DEBUG:
        if retval:
            _logger.debug(f"retval = isinstance({value_str}, {tstr}) is True")
        else:
            typ: str = eval(f"type({value_str})")  # pylint: disable=eval-used
            _logger.debug(f"retval = isinstance({value_str}, {tstr}) is False. {value_str} is of type {typ}.")

    return retval
