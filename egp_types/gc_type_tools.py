""" GC type tools.

NOTE: Cannot depend on any *GC types. This is a circular dependency.
"""
from hashlib import sha256
from logging import DEBUG, Logger, NullHandler, getLogger
from pprint import pformat
from typing import TYPE_CHECKING, Any, Literal, LiteralString

from numpy import asarray, uint8, int32, int64, float32
from numpy.typing import NDArray

from .ep_type import asint

if TYPE_CHECKING:
    from hashlib import _Hash


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# GC signatre None type management
# It is space efficient to have None types in the DB for signatures but not in the cache.
# In the GPC a None type is represented by a 0 SHA256
NULL_SIGNATURE_BYTES: bytes = b"\x00" * 32
NULL_SIGNATURE_ARRAY: NDArray[uint8] = asarray([0] * 32, dtype=uint8)

# Evolve a pGC after this many 'uses'.
# MUST be a power of 2
M_CONSTANT: int = 1 << 4
M_MASK: int = M_CONSTANT - 1
NUM_PGC_LAYERS = 16
# With M_CONSTANT = 16 & NUM_PGC_LAYERS = 16 it will take 16**16 (== 2**64 == 18446744073709551616)
# population individual evolutions to require a 17th layer (and that is assuming all PGC's are
# children of the one in the 16th layer). Thats about 5.8 billion evolutions per second for
# 100 years. A million super fast cores doing 5.8 million per second...only an outside chance
# of hitting the limit if Erasmus becomes a global phenomenon and is not rewritten! Sensibly future proofed.

# Constants
INT32_ZERO = int32(0)
INT32_ONE = int32(1)
INT32_MINUS_ONE = int32(-1)
INT64_ZERO = int64(0)
FLOAT32_ZERO = float32(0.0)
FLOAT32_ONE = float32(1.0)

# FIXME: This is duplicated in egp_types.gc_type. Consider creating a seperate module of
# field definitions.
# PROPERTIES must define the bit position of all the properties listed in
# the "properties" field of the entry_format.json definition.
PROPERTIES: dict[str, int] = {
    "extended": 1 << 0,
    "constant": 1 << 1,
    "conditional": 1 << 2,
    "deterministic": 1 << 3,
    "memory_modify": 1 << 4,
    "object_modify": 1 << 5,
    "physical": 1 << 6,
    "arithmetic": 1 << 16,
    "logical": 1 << 17,
    "bitwise": 1 << 18,
    "boolean": 1 << 19,
    "sequence": 1 << 20,
}
PHYSICAL_PROPERTY: int = PROPERTIES["physical"]
LAYER_COLUMNS: tuple[LiteralString, ...] = (
    "evolvability",
    "fitness",
    "e_count",
    "f_count",
    "if",
)
LAYER_COLUMNS_RESET: dict[str, int] = {"e_count": 1, "f_count": 1}
_GL_EXCLUDE_COLUMNS: tuple[LiteralString, ...] = (
    "signature",
    "gca",
    "gcb",
    "pgc",
    "ancestor_a",
    "ancestor_b",
    "creator",
)
_SIGN: tuple[Literal[1], Literal[-1]] = (1, -1)


def is_pgc(genetic_code: Any) -> bool:
    """Determine if a GC is a PGC.

    Args
    ----
    gc(dict-like): A GC dict-like object.

    Returns
    -------
    (bool): True if gc is a pGC else False
    """
    if _LOG_DEBUG:
        # More juicy test for consistency
        # TODO: More conditions can be added
        # Check the physical property?
        input_types: list[int] = genetic_code.get("input_types", [])
        output_types: list[int] = genetic_code.get("output_types", [])
        pgc_inputs: bool = any(asint(t) < 0 for t in input_types)
        pgc_outputs: bool = any(asint(t) < 0 for t in output_types)
        pgc_check: bool = (pgc_inputs and pgc_outputs) and (genetic_code.get("pgc_fitness", None) is not None)
        ggc_check: bool = genetic_code.get("pgc_fitness", None) is None
        if not (pgc_check or ggc_check) and not (pgc_check and ggc_check):
            _logger.debug(
                f"Inconsistent GC definition: Is it a gGC or a pGC?:\n{pformat(genetic_code, indent=4, sort_dicts=True, width=140)}"
            )
            raise ValueError(
                f"Inconsistent GC definition: Is it a gGC or a pGC?: {genetic_code['ref']}\n\t{pgc_inputs}, {pgc_outputs},"
                f" {(pgc_inputs and pgc_outputs)}, {(genetic_code.get('pgc_fitness', None) is not None)}"
            )
    return genetic_code.get("pgc_fitness", None) is not None


def define_signature(mgc: Any) -> bytes:
    """Define the signature of a genetic code.

    The signature for a codon GC is slightly different to a regular GC.

    Args
    ----
    mgc: Has all the mGC required fields.

    Returns
    -------
    SHA256 bytes object.
    """
    # NOTE: This needs to be very specific and stand the test of time!
    # Also NOTE: Ancestory is bound in which means if ancestors end up being culled we will
    # need a way to point to the youngest existing ancestor.
    gca_hex: str = "0" * 64 if mgc["gca"] is None else mgc["gca"].hex()
    gcb_hex: str = "0" * 64 if mgc["gcb"] is None else mgc["gcb"].hex()
    ancestor_a_hex: str = "0" * 64 if mgc["gca"] is None else mgc["gca"].hex()
    ancestor_b_hex: str = "0" * 64 if mgc["gcb"] is None else mgc["gcb"].hex()
    string: str = pformat(mgc["graph"], indent=0, sort_dicts=True, width=65535, compact=True)
    string += gca_hex + gcb_hex + ancestor_a_hex + ancestor_b_hex + str(mgc["creator"])

    # If it is a codon glue on the mandatory definition
    if "generation" in mgc and mgc["generation"] == 0:
        if "meta_data" in mgc and "function" in mgc["meta_data"]:
            string += mgc["meta_data"]["function"]["python3"]["0"]["inline"]
            if "code" in mgc["meta_data"]["function"]["python3"]["0"]:
                string += mgc["meta_data"]["function"]["python3"]["0"]["code"]

    return sha256(string.encode()).digest()


def signature(  # pylint: disable=dangerous-default-value
    gca_sig: memoryview, gcb_sig: memoryview, i_data: memoryview, o_data: memoryview, con_data: memoryview, meta_data: dict[str, Any] = {}
) -> NDArray:
    """Return the signature of a genetic code."""
    # NOTE: This needs to be very specific and stand the test of time!
    hash_obj: _Hash = sha256(gca_sig)
    hash_obj.update(gcb_sig)
    hash_obj.update(i_data)
    hash_obj.update(o_data)
    hash_obj.update(con_data)
    if "function" in meta_data:
        hash_obj.update(meta_data["function"]["python3"]["0"]["inline"].encode())
        if "code" in meta_data["function"]["python3"]["0"]:
            hash_obj.update(meta_data["function"]["python3"]["0"]["code"].encode())
    return asarray(bytearray(hash_obj.digest()), dtype=uint8)


def app_sig_to_array(sig: bytes | memoryview | None) -> NDArray[uint8]:
    """Convert the application signature to a numpy array."""
    return asarray(sig, dtype=uint8) if sig is not None else NULL_SIGNATURE_ARRAY
