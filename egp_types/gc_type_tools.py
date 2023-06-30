""" GC type tools.

NOTE: Cannot depend on any *GC types. This is a circular dependency.
"""
from hashlib import sha256
from logging import DEBUG, Logger, NullHandler, getLogger
from pprint import pformat
from typing import Literal, LiteralString, Any


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


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
    "sequence": 1 << 20
}
PHYSICAL_PROPERTY: int = PROPERTIES['physical']
LAYER_COLUMNS: tuple[LiteralString, ...] = (
    "evolvability",
    "fitness",
    "e_count",
    "f_count",
    "if"
)
LAYER_COLUMNS_RESET: dict[str, int] = {
    "e_count": 1,
    "f_count": 1
}
_GL_EXCLUDE_COLUMNS: tuple[LiteralString, ...] = (
    'signature',
    'gca',
    'gcb',
    'pgc',
    'ancestor_a',
    'ancestor_b',
    'creator'
)
_SIGN: tuple[Literal[1], Literal[-1]] = (1, -1)


def is_pgc(genetic_code: Any):
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
        input_types: list[int] = genetic_code.get('input_types', [])
        inputs: list[int] = genetic_code.get('inputs', [])
        output_types: list[int] = genetic_code.get('output_types', [])
        outputs: list[int] = genetic_code.get('outputs', [])
        pgc_inputs: bool = bool(input_types) and input_types[0] == -3 and len(inputs) == 1
        pgc_outputs: bool = bool(output_types) and output_types[0] == -3 and len(outputs) == 1
        check: bool = (pgc_inputs and pgc_outputs) == (genetic_code.get('pgc_fitness', None) is not None)
        if not check:
            raise ValueError(
                f"PGC is not a PGC!: {genetic_code['ref']}\n\t{pgc_inputs}, {pgc_outputs}, {genetic_code.get('pgc_fitness', None)},"
                f" {(pgc_inputs and pgc_outputs)}, {(genetic_code.get('pgc_fitness', None) is not None)}")
    return genetic_code.get('pgc_fitness', None) is not None


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
    gca_hex: str = '0' * 64 if mgc['gca'] is None else mgc['gca'].hex()
    gcb_hex: str = '0' * 64 if mgc['gcb'] is None else mgc['gcb'].hex()
    ancestor_a_hex: str = '0' * 64 if mgc['gca'] is None else mgc['gca'].hex()
    ancestor_b_hex: str = '0' * 64 if mgc['gcb'] is None else mgc['gcb'].hex()
    string: str = pformat(mgc['graph'], indent=0, sort_dicts=True, width=65535, compact=True)
    string += gca_hex + gcb_hex + ancestor_a_hex + ancestor_b_hex + str(mgc['creator'])

    # If it is a codon glue on the mandatory definition
    if "generation" in mgc and mgc["generation"] == 0:
        if "meta_data" in mgc and "function" in mgc["meta_data"]:
            string += mgc["meta_data"]["function"]["python3"]["0"]["inline"]
            if 'code' in mgc["meta_data"]["function"]["python3"]["0"]:
                string += mgc["meta_data"]["function"]["python3"]["0"]["code"]

    return sha256(string.encode()).digest()
