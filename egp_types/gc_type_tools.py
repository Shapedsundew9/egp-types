from logging import DEBUG, NullHandler, getLogger
from random import choice, getrandbits
from hashlib import sha256
from pprint import pformat


_logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG = _logger.isEnabledFor(DEBUG)


# Pretty print for references
_OVER_MAX = 1 << 64
_MASK = _OVER_MAX - 1
ref_str = lambda x: 'None' if x is None else f"{((_OVER_MAX + x) & _MASK):016x}"


# Evolve a pGC after this many 'uses'.
# MUST be a power of 2
M_CONSTANT = 1 << 4
M_MASK = M_CONSTANT - 1
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
PROPERTIES = {
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
PHYSICAL_PROPERTY = PROPERTIES['physical']
LAYER_COLUMNS = (
    "evolvability",
    "fitness",
    "e_count",
    "f_count",
    "if"
)
LAYER_COLUMNS_RESET = {
    "e_count": 1,
    "f_count": 1
}
_GL_EXCLUDE_COLUMNS = (
    'signature',
    'gca',
    'gcb',
    'pgc',
    'ancestor_a',
    'ancestor_b',
    'creator'
)
_SIGN = (1, -1)


def is_pgc(gc):
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
        it = gc.get('input_types', [])
        i = gc.get('inputs', [])
        ot = gc.get('output_types', [])
        o = gc.get('outputs', [])
        pgc_inputs = bool(it) and it[0] == -3 and len(i) == 1
        pgc_outputs = bool(ot) and ot[0] == -3 and len(o) == 1
        check = (pgc_inputs and pgc_outputs) == (gc.get('pgc_fitness', None) is not None)
        if not check:
            ValueError(f"PGC is not a PGC!: {gc['ref']}\n\t{pgc_inputs}, {pgc_outputs}, {gc.get('pgc_fitness', None)},"
                          f" {(pgc_inputs and pgc_outputs)}, {(gc.get('pgc_fitness', None) is not None)}")
    return gc.get('pgc_fitness', None) is not None


# https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries
def merge(a, b, path=None):
    """Merge dict b into a recursively. a is modified.

    This function is equivilent to a.update(b) if b contains no dictionary values with
    the same key as in a.

    If there are dictionaries
    in b that have the same key as a then those dictionaries are merged in the same way.
    Keys in a & b (or common key'd sub-dictionaries) where one is a dict and the other
    some other type raise an exception.

    Args
    ----
    a (dict): Dictionary to merge in to.
    b (dict): Dictionary to merge.

    Returns
    -------
    a (modified)
    """
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def define_signature(gc):
    """Define the signature of a genetic code.

    The signature for a codon GC is slightly different to a regular GC.

    Args
    ----
    gc(dict): Must at least be an mCodon.

    Returns
    -------
    (str): Lowercase hex SHA256 string.
    """
    # NOTE: This needs to be very specific and stand the test of time!
    gca_hex = '0' * 64 if gc['gca'] is None else gc['gca']
    gcb_hex = '0' * 64 if gc['gcb'] is None else gc['gcb']
    string = pformat(gc['graph'], indent=0, sort_dicts=True, width=65535, compact=True) + gca_hex + gcb_hex

    # If it is a codon glue on the mandatory definition
    if "generation" in gc and gc["generation"] == 0:
        if "meta_data" in gc and "function" in gc["meta_data"]:
            string += gc["meta_data"]["function"]["python3"]["0"]["inline"]
            if 'code' in gc["meta_data"]["function"]["python3"]["0"]:
                string += gc["meta_data"]["function"]["python3"]["0"]["code"]
    return sha256(string.encode()).digest()