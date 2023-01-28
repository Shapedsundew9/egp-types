"""Validation of gc_type."""

from egp_types.eGC import eGC
from egp_types.md_table import md_table


def test_md_table():
    """Generate the markdown table of xGC attributes."""
    md_table()


def test_instanciate_eGC_n0():
    """Validate instanciation of an eGC().

    An eGC has required fields so will raise a ValueError in instanciated
    without them defined.
    """
    try:
        assert eGC(sv=False)
    except ValueError:
        pass


