"""Data type conversions for GC fields.

The need for type conversions is driven by:
    a) Efficient database storage types
    b) Efficient python code execution types
    c) Limitations of human readable file formats i.e. JSON
"""
from base64 import b64decode, b64encode
from datetime import datetime
from json import dumps, loads
from typing import Union
from uuid import UUID
from zlib import compress, decompress

from egp_types.gc_type_tools import PROPERTIES


def json_obj_to_str(obj: Union[dict, list, None]) -> Union[str, None]:
    """Dump a python object that is a valid JSON structure to a string.

    Args
    ----
    obj must be a JSON compatible python object

    Returns
    -------
    JSON string representation of obj
    """
    return None if obj is None else dumps(obj)


def str_to_json_obj(obj: Union[str, None]) -> Union[dict, list, None]:
    """Dump a python object that is a valid JSON structure to a string.

    Args
    ----
    obj must be a JSON compatible string

    Returns
    -------
    python object representation of obj
    """
    return None if obj is None else loads(obj)


def encode_effective_pgcs(obj: Union[list[list[bytes]], None]) -> Union[list[list[bytes]], None]:
    """Encode the effective_pgcs list of lists of binary signatures into a JSON compatible object.

    Args
    ----
    obj is the list of lists of 32 byte binary signatures

    Returns
    -------
    List of lists of base 64 encoded strings
    """
    if obj is None:
        return None

    return [[b64encode(signature) for signature in layer] for layer in obj]


def decode_effective_pgcs(obj: Union[list[list[str]], None]) -> Union[list[list[bytes]], None]:
    """Encode the effective_pgcs list of lists of binary signatures into a JSON compatible object.

    Args
    ----
    obj is the list of lists of base 64 encoded signature strings

    Returns
    -------
    List of lists of binary signatures
    """
    if obj is None:
        return None

    return [[b64decode(signature) for signature in layer] for layer in obj]


def compress_json(obj) -> bytes | memoryview | bytearray | None:
    """Compress a JSON dict object.

    Args
    ----
    obj (dict): Must be a JSON compatible dict.

    Returns
    -------
    (bytes): zlib compressed JSON string.
    """
    # TODO: Since the vast majority of data looks the same but is broken into many objects
    # it would be more efficient to use a compression algorithm that does not embedded the
    # compression token dictionary.
    if isinstance(obj, dict):
        return compress(dumps(obj).encode())
    if isinstance(obj, memoryview) or isinstance(obj, bytearray) or isinstance(obj, bytes):
        return obj
    if obj is None:
        return None
    raise TypeError("Un-encodeable type '{}': Expected 'dict' or byte type.".format(type(obj)))


def decompress_json(obj):
    """Decompress a compressed JSON dict object.

    Args
    ----
    obj (bytes): zlib compressed JSON string.

    Returns
    -------
    (dict): JSON dict.
    """
    return None if obj is None else loads(decompress(obj).decode())


def memoryview_to_bytes(obj):
    """Convert a memory view to a bytes object.

    Args
    ----
    obj (memoryview or NoneType):

    Returns
    -------
    (bytes or NoneType)
    """
    return None if obj is None else bytes(obj)


def str_to_sha256(obj):
    """Convert a hexidecimal string to a bytearray.

    Args
    ----
    obj (str): Must be a hexadecimal string.

    Returns
    -------
    (bytearray): bytearray representation of the string.
    """
    if isinstance(obj, str):
        return bytearray.fromhex(obj)
    if isinstance(obj, memoryview) or isinstance(obj, bytearray) or isinstance(obj, bytes):
        return obj
    if obj is None:
        return None
    raise TypeError("Un-encodeable type '{}': Expected 'str' or byte type.".format(type(obj)))


def str_to_UUID(obj):
    """Convert a UUID formated string to a UUID object.

    Args
    ----
    obj (str): Must be a UUID formated hexadecimal string.

    Returns
    -------
    (uuid): UUID representation of the string.
    """
    if isinstance(obj, str):
        return UUID(obj)
    if isinstance(obj, UUID):
        return obj
    if obj is None:
        return None
    raise TypeError("Un-encodeable type '{}': Expected 'str' or UUID type.".format(type(obj)))


def str_to_datetime(obj):
    """Convert a datetime formated string to a datetime object.

    Args
    ----
    obj (str): Must be a datetime formated string.

    Returns
    -------
    (datetime): datetime representation of the string.
    """
    if isinstance(obj, str):
        return datetime.strptime(obj, "%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(obj, datetime):
        return obj
    if obj is None:
        return None
    raise TypeError("Un-encodeable type '{}': Expected 'str' or datetime type.".format(type(obj)))


def sha256_to_str(obj):
    """Convert a bytearray to its lowercase hexadecimal string representation.

    Args
    ----
    obj (bytearray): bytearray representation of the string.

    Returns
    -------
    (str): Lowercase hexadecimal string.
    """
    return None if obj is None else obj.hex()


def UUID_to_str(obj):
    """Convert a UUID to its lowercase hexadecimal string representation.

    Args
    ----
    obj (UUID): UUID representation of the string.

    Returns
    -------
    (str): Lowercase hexadecimal UUID string.
    """
    return None if obj is None else str(obj)


def datetime_to_str(obj):
    """Convert a datetime to its string representation.

    Args
    ----
    obj (datetime): datetime representation of the string.

    Returns
    -------
    (str): datetime string.
    """
    return None if obj is None else obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def encode_properties(obj):
    """Encode the properties dictionary into its integer representation.

    The properties field is a dictionary of properties to boolean values. Each
    property maps to a specific bit of a 64 bit value as defined
    by the _PROPERTIES dictionary.

    Args
    ----
    obj(dict): Properties dictionary.

    Returns
    -------
    (int): Integer representation of the properties dictionary.
    """
    if isinstance(obj, dict):
        bitfield = 0
        for k, v in filter(lambda x: x[1], obj.items()):
            bitfield |= PROPERTIES[k]
        return bitfield
    if isinstance(obj, int):
        return obj
    raise TypeError("Un-encodeable type '{}': Expected 'dict' or integer type.".format(type(obj)))


def decode_properties(obj):
    """Decode the properties dictionary from its integer representation.

    The properties field is a dictionary of properties to boolean values. Each
    property maps to a specific bit of a 64 bit value as defined
    by the _PROPERTIES dictionary.

    Args
    ----
    obj(int): Integer representation of the properties dictionary.

    Returns
    -------
    (dict): Properties dictionary.
    """
    return {b: bool(f & obj) for b, f in PROPERTIES.items()}
