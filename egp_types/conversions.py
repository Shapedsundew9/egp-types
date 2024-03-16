"""Data type conversions for GC fields.

The need for type conversions is driven by:
    a) Efficient database storage types
    b) Efficient python code execution types
    c) Limitations of human readable file formats i.e. JSON
"""
from base64 import b64decode, b64encode
from json import dumps, loads
from zlib import compress, decompress
from numpy import array, uint8, frombuffer
from numpy.typing import NDArray

from egp_types.gc_type_tools import PROPERTIES


def json_obj_to_str(obj: dict | list | None) -> str | None:
    """Dump a python object that is a valid JSON structure to a string.

    Args
    ----
    obj must be a JSON compatible python object

    Returns
    -------
    JSON string representation of obj
    """
    return None if obj is None else dumps(obj)


def str_to_json_obj(obj: str | None) -> dict | list | None:
    """Dump a python object that is a valid JSON structure to a string.

    Args
    ----
    obj must be a JSON compatible string

    Returns
    -------
    python object representation of obj
    """
    return None if obj is None else loads(obj)


def encode_effective_pgcs(obj: list[list[bytes]] | None) -> list[list[bytes]] | None:
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


def decode_effective_pgcs(obj: list[list[str]] | None) -> list[list[bytes]] | None:
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


def compress_json(obj: dict | list | None) -> bytes | memoryview | bytearray | None:
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
    raise TypeError(f"Un-encodeable type '{type(obj)}': Expected 'dict' or byte type.")


def decompress_json(obj: bytes | None) -> dict | list | None:
    """Decompress a compressed JSON dict object.

    Args
    ----
    obj (bytes): zlib compressed JSON string.

    Returns
    -------
    (dict): JSON dict.
    """
    return None if obj is None else loads(decompress(obj).decode())


def memoryview_to_bytes(obj: memoryview | None) -> bytes | None:
    """Convert a memory view to a bytes object.

    Args
    ----
    obj (memoryview or NoneType):

    Returns
    -------
    (bytes or NoneType)
    """
    return None if obj is None else bytes(obj)


def memoryview_to_ndarray(obj: memoryview | None) -> NDArray | None:
    """Convert a memory view to a 32 uint8 numpy ndarray.

    Args
    ----
    obj (memoryview or NoneType):

    Returns
    -------
    (numpy.ndarray or NoneType)
    """
    return None if obj is None else frombuffer(obj, dtype=uint8, count=32)


def ndarray_to_memoryview(obj: NDArray | None) -> memoryview | None:
    """Convert a numpy 32 uint8 ndarray to a memory view.

    Args
    ----
    obj (numpy.ndarray or NoneType):

    Returns
    -------
    (memoryview or NoneType)
    """
    if isinstance(obj, bytes):
        return memoryview(obj)
    return None if obj is None else obj.data


def ndarray_to_bytes(obj: NDArray | None) -> bytes | None:
    """Convert a numpy 32 uint8 ndarray to a bytes object.

    Args
    ----
    obj (numpy.ndarray or NoneType):

    Returns
    -------
    (bytes or NoneType)
    """
    if isinstance(obj, bytes):
        return obj
    return None if obj is None else obj.tobytes()


def encode_properties(obj: dict[str, bool] | int | None) -> int:
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
        bitfield: int = 0
        for k, _ in filter(lambda x: x[1], obj.items()):
            bitfield |= PROPERTIES[k]
        return bitfield
    if isinstance(obj, int):
        return obj
    if obj is None:
        return 0
    raise TypeError(f"Un-encodeable type '{type(obj)}': Expected 'dict' or integer type.")


def decode_properties(obj: int | dict[str, bool] | None) -> dict[str, bool]:
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
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, int):
        return {b: bool(f & obj) for b, f in PROPERTIES.items()}
    if obj is None:
        return {b: False for b, f in PROPERTIES.items()}
    raise TypeError(f"Un-encodeable type '{type(obj)}': Expected 'dict' or integer type.")
