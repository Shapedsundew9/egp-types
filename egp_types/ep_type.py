"""Manages endpoint type interactions.

Endpoint types are identified by a signed 16-bit value or
a fully qualified name.

Erasmus GP types have values < 0.
An invalid ep type has the value -32768
NoneType == 0
All other types values are > 0
"""


from enum import IntEnum
from json import load
from logging import NullHandler, getLogger
from os.path import dirname, join
from hashlib import blake2b

_logger = getLogger(__name__)
_logger.addHandler(NullHandler())


# Load type data
with open(join(dirname(__file__), "data/ep_types.json"), "r") as file_ptr:
    ep_type_lookup = load(file_ptr)
    ep_type_lookup['v2n'] = {int(k): v for k, v in ep_type_lookup['v2n'].items()}
    ep_type_lookup['n2v'] = {k: int(v) for k, v in ep_type_lookup['n2v'].items()}
    ep_type_lookup['instanciation'] = {int(k): v for k, v in ep_type_lookup['instanciation'].items()}


_EGP_SPECIAL_TYPE_LIMIT = -32767
_EGP_PHYSICAL_TYPE_LIMIT = -32369
_EGP_REAL_TYPE_LIMIT = 0
_EGP_TYPE_LIMIT = 32769

def _SPECIAL_TYPE_FILTER(v): return v < _EGP_PHYSICAL_TYPE_LIMIT and v >= _EGP_SPECIAL_TYPE_LIMIT
def _PHYSICAL_TYPE_FILTER(v): return v < _EGP_REAL_TYPE_LIMIT and v >= _EGP_PHYSICAL_TYPE_LIMIT
def _REAL_TYPE_FILTER(v): return v < _EGP_TYPE_LIMIT and v >= _EGP_REAL_TYPE_LIMIT

SPECIAL_EP_TYPE_VALUES = tuple((v for v in filter(_SPECIAL_TYPE_FILTER, ep_type_lookup['n2v'].values())))
PHYSICAL_EP_TYPE_VALUES = tuple((v for v in filter(_PHYSICAL_TYPE_FILTER, ep_type_lookup['n2v'].values())))
REAL_EP_TYPE_VALUES = tuple((v for v in filter(_REAL_TYPE_FILTER, ep_type_lookup['n2v'].values())))
_logger.info(f"{len(SPECIAL_EP_TYPE_VALUES)} special endpoint types identified.")
_logger.info(f"{len(PHYSICAL_EP_TYPE_VALUES)} physical endpoint types identified.")
_logger.info(f"{len(REAL_EP_TYPE_VALUES)} real endpoint types identified.")

INVALID_EP_TYPE_NAME = 'egp_invalid_type'
INVALID_EP_TYPE_VALUE = -32768
UNKNOWN_EP_TYPE_NAME = 'egp_unknown_type'
UNKNOWN_EP_TYPE_VALUE = -32767

ep_type_lookup['n2v'][INVALID_EP_TYPE_NAME] = INVALID_EP_TYPE_VALUE
ep_type_lookup['v2n'][INVALID_EP_TYPE_VALUE] = INVALID_EP_TYPE_NAME
ep_type_lookup['instanciation'][INVALID_EP_TYPE_VALUE] = [None] * 5
ep_type_lookup['n2v'][UNKNOWN_EP_TYPE_NAME] = UNKNOWN_EP_TYPE_VALUE
ep_type_lookup['v2n'][UNKNOWN_EP_TYPE_VALUE] = UNKNOWN_EP_TYPE_NAME
ep_type_lookup['instanciation'][UNKNOWN_EP_TYPE_VALUE] = [None] * 5


class inst(IntEnum):
    """EP type 'instanciation' value list index."""

    PACKAGE = 0  # (str) package name
    VERSION = 1  # (str) package version number
    MODULE = 2  # (str) module name
    NAME = 3    # (str) object name
    PARAM = 4   # (bool or None)


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


def import_str(ep_type_int):
    """Return the import string for ep_type_int.

    Args
    ----
    ep_type_int (int): A valid ep_type value.

    Returns
    -------
    (str): The import e.g. 'from numpy import float32 as numpy_float32'
    """
    i = ep_type_lookup['instanciation'][ep_type_int]
    if i[inst.MODULE] is None:
        return 'None'
    package = '' if i[inst.PACKAGE] is None else i[inst.PACKAGE] + '.'
    return f'from {package}{i[inst.MODULE]} import {i[inst.NAME]} as {i[inst.MODULE]}_{i[inst.NAME]}'


# If a type does not exist on this system remove it (all instances will be treated as INVALID)
# NOTE: This would cause a circular dependency with gc_type if GC types were not filtered out
# We can assume GC types will be defined for the contexts they are used.
def func(x):
    """Filter function."""
    return x[1][inst.PACKAGE] is not None and x[1][inst.PACKAGE] != 'egp_types'


for ep_type_int, data in tuple(filter(func, ep_type_lookup['instanciation'].items())):
    try:
        exec(import_str(ep_type_int))
    except ModuleNotFoundError:
        _logger.warning(f"Module '{data[inst.MODULE]}' was not found. '{data[inst.NAME]}' will be treated as an INVALID type.")
        del ep_type_lookup['n2v'][ep_type_lookup['v2n'][ep_type_int]]
        del ep_type_lookup['instanciation'][ep_type_int]
        del ep_type_lookup['v2n'][ep_type_int]
    else:
        _logger.info(import_str(ep_type_int))


def func(x):
    """Filter function."""
    return x[inst.PACKAGE] is not None and x[inst.PACKAGE] == 'egp_types'


_GC_TYPE_NAMES = []
for i in tuple(filter(func, ep_type_lookup['instanciation'].values())):
    _GC_TYPE_NAMES.append(f'{i[inst.MODULE]}_{i[inst.NAME]}')

# Must be defined after the imports
EP_TYPE_NAMES = set(ep_type_lookup['n2v'].keys())
EP_TYPE_VALUES = set(ep_type_lookup['v2n'].keys())


def validate(obj, vt=vtype.EP_TYPE_INT):
    """Validate an object as an EP type.

    NOTE: GC types e.g. eGC, mGC etc. cannot be instance strings as they would require
    a circular import. However, since GC types are under the full control of EGP there
    should be no need to try and introspect an instance string for a GC type.

    Args
    ----
    object (object): See description above.
    vt (vtype): The interpretation of the object. See vtype definition.:

    Returns
    -------
    (bool) True if the type is defined else false.
    """
    if vt == vtype.TYPE_OBJECT:
        return fully_qualified_name(obj()) in EP_TYPE_NAMES
    if vt == vtype.OBJECT:
        return fully_qualified_name(obj) in EP_TYPE_NAMES
    if vt == vtype.INSTANCE_STR:
        try:
            name = fully_qualified_name(eval(obj))
        except NameError:
            # If it looks like a GC type instanciation assume it is OK.
            return any([x + '(' in obj for x in _GC_TYPE_NAMES])
        return name in EP_TYPE_NAMES
    if vt == vtype.EP_TYPE_STR:
        return obj != INVALID_EP_TYPE_NAME and obj in EP_TYPE_NAMES
    return obj != INVALID_EP_TYPE_VALUE and obj in EP_TYPE_VALUES


def asint(obj, vt=vtype.EP_TYPE_STR):
    """Return the EP type value for an object.

    NOTE: GC types e.g. eGC, mGC etc. cannot be instance strings as they would require
    a circular import. However, since GC types are under the full control of EGP there
    should be no need to try and introspect an instance string for a GC type.

    Args
    ----
    object (object): See description above.
    vt (vtype): The interpretation of the object. See vtype definition.:

    Returns
    -------
    (int) The EP type of the object (may be egp.invalid_type)
    """
    if vt == vtype.TYPE_OBJECT:
        return ep_type_lookup['n2v'].get(fully_qualified_name(obj()), INVALID_EP_TYPE_VALUE)
    if vt == vtype.OBJECT:
        return ep_type_lookup['n2v'].get(fully_qualified_name(obj), INVALID_EP_TYPE_VALUE)
    if vt == vtype.INSTANCE_STR:
        try:
            ep_type_name = fully_qualified_name(eval(obj))
        except NameError:
            # If it looks like a GC type instanciation assume it is OK.
            ep_type_name = INVALID_EP_TYPE_NAME
            for x in _GC_TYPE_NAMES:
                if x + '(' in obj:
                    ep_type_name = 'egp_types.' + x
                    break
        return ep_type_lookup['n2v'].get(ep_type_name, INVALID_EP_TYPE_VALUE)
    if vt == vtype.EP_TYPE_STR:
        return ep_type_lookup['n2v'].get(obj, INVALID_EP_TYPE_VALUE)
    return obj


def asstr(obj, vt=vtype.EP_TYPE_INT):
    """Return the EP type string for an object.

    NOTE: GC types e.g. eGC, mGC etc. cannot be instance strings as they would require
    a circular import. However, since GC types are under the full control of EGP there
    should be no need to try and introspect an instance string for a GC type.

    Args
    ----
    object (object): See description above.
    vt (vtype): The interpretation of the object. See vtype definition.


    Returns
    -------
    (str) The EP type of the object (may be egp.invalid_type)
    """
    if vt == vtype.TYPE_OBJECT:
        ep_type_name = fully_qualified_name(obj())
        return ep_type_name if ep_type_name in EP_TYPE_NAMES else INVALID_EP_TYPE_NAME
    if vt == vtype.OBJECT:
        ep_type_name = fully_qualified_name(obj)
        return ep_type_name if ep_type_name in EP_TYPE_NAMES else INVALID_EP_TYPE_NAME
    if vt == vtype.INSTANCE_STR:
        try:
            ep_type_name = fully_qualified_name(eval(obj))
        except NameError:
            # If it looks like a GC type instanciation assume it is OK.
            for x in _GC_TYPE_NAMES:
                if x + '(' in obj:
                    return 'egp_types.' + x
            return INVALID_EP_TYPE_NAME
        return ep_type_name if ep_type_name in EP_TYPE_NAMES else INVALID_EP_TYPE_NAME
    if vt == vtype.EP_TYPE_INT:
        return ep_type_lookup['v2n'].get(obj, INVALID_EP_TYPE_NAME)
    return obj


def fully_qualified_name(obj):
    """Return the fully qualified type name for obj.

    Args
    ----
    obj (object): Any object

    Returns
    -------
    (str): Fully qualified type name.
    """
    return obj.__class__.__module__ + '_' + obj.__class__.__qualname__


def compatible(a, b):
    """If EP type a is compatible with gc type b return True else False.

    a and b must be of the same type.

    TODO: Define what compatible means. For now it means 'exactly the same type'.

    Args
    ----
    a (int or str): A valid ep_type value or name.
    b (int or str): A valid ep_type value or name.

    Returns
    -------
    (bool): True if a and b are compatible.
    """
    return a == b


def type_str(ep_type_int):
    """Return the type string for ep_type_int.

    Args
    ----
    ep_type_int (int): A valid ep_type value.

    Returns
    -------
    (str): The type string e.g. 'int' or 'str'
    """
    i = ep_type_lookup['instanciation'][ep_type_int]
    return i[inst.NAME] if i[inst.MODULE] is None else f'{i[inst.MODULE]}_{i[inst.NAME]}'


def instance_str(ep_type_int, param_str=''):
    """Return the instanciation string for ep_type_int.

    Args
    ----
    ep_type_int (int): A valid ep_type value.
    param_str (str): A string to be used as instanciation parameters.

    Returns
    -------
    (str): The instanciation e.g. numpy_float32(<param_str>)
    """
    inst_str = type_str(ep_type_int)
    if ep_type_lookup['instanciation'][ep_type_int][inst.PARAM]:
        inst_str += f'({param_str})'
    return inst_str


def interface_definition(xputs, vt=vtype.TYPE_OBJECT):
    """Create an interface definition from xputs.

    Used to define the inputs or outputs of a GC from an iterable
    of types, objects or EP definitions.

    Args
    ----
    xputs (iterable(object)): Object is of the type defined by vt.
    vt (vtype): The interpretation of the object. See definition of vtype.

    Returns
    -------
    tuple(list(ep_type_int), list(ep_type_int), list(int)): A list of the xputs as EP type in value
        format, a list of the EP types in xputs in value format in ascending order and a list of
        indexes into it in the order of xputs.
    """
    xput_eps = tuple((asint(x, vt) for x in xputs))
    xput_types = sorted(set(xput_eps))
    return xput_eps, xput_types, bytes([xput_types.index(x) for x in xput_eps])


def unordered_interface_hash(input_eps, output_eps):
    """Create a 64-bit hash of the population interface definition.

    The interface hash is order agnostic i.e.

    (float, int, float) has the same hash as (float, float, int) has
    the same hash as (int, float, float).

    Args
    ----
    input_eps (iterable(int)): Iterable of input EP types.
    output_eps (iterable(int)): Iterable of output EP types.

    Returns
    -------
    (int): 64 bit hash as a signed 64 bit int.
    """
    h = blake2b(digest_size=8)
    for i in sorted(input_eps):
        h.update(i.to_bytes(2, 'big'))
    for o in sorted(output_eps):
        h.update(o.to_bytes(2, 'big'))
    a = int.from_bytes(h.digest(), 'big')
    return (0x7FFFFFFFFFFFFFFF & a) - (a & (1 << 63))


def ordered_interface_hash(input_types, output_types, inputs, outputs):
    """Create a 64-bit hash of the population interface definition.

    The interface hash is specific to the order and type in the inputs
    and outputs. This is important in population individuals.

    Args
    ----
    input_types (iterable(int)): Iterable of input EP types in ascending order.
    output_types (iterable(int)): Iterable of output EP types in ascending order.
    inputs (bytes): Indices into input_types for the input parameters.
    outputs (bytes): Indices into output_types for the input parameters.

    Returns
    -------
    (int): 64 bit hash as a signed 64 bit int.
    """
    h = blake2b(digest_size=8)
    for i in input_types:
        h.update(i.to_bytes(2, 'big'))
    for o in sorted(output_types):
        h.update(o.to_bytes(2, 'big'))
    h.update(inputs)
    h.update(outputs)
    a = int.from_bytes(h.digest(), 'big')
    return (0x7FFFFFFFFFFFFFFF & a) - (a & (1 << 63))
