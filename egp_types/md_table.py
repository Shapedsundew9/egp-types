from ._GC import _GC
from .eGC import eGC
from .mGC import mGC
from .xgc_validator import XGC_ENTRY_SCHEMA


# GitHub Markdown Emoji's
_DEFINABLE_MD = ":large_blue_circle:"
_REQUIRED_MD = ":black_circle:"


def md_string(gct, key):
    """Generate the GitHub MD string relevant to the key for gct."""
    if key not in gct.validator.schema:
        return ""
    if 'default' in gct.validator.schema[key] or 'default_setter' in gct.validator.schema[key]:
        return _DEFINABLE_MD
    return _REQUIRED_MD


def md_table():
    """Create a GitHub Markdown table showing the requirements of each field for each GC type."""
    gcts = (
        _GC(sv=True),
        eGC(sv=True),
        mGC(sv=True)
    )
    with open('gc_type_table.md', 'w') as file_ptr:
        file_ptr.write("GC Type Field Requirements\n")
        file_ptr.write("==========================\n\n")
        file_ptr.write(_DEFINABLE_MD + ': Defined if not set, ' + _REQUIRED_MD + ': Required.\n\n')
        file_ptr.write('| Field | ' + ' | '.join((x.__class__.__qualname__ for x in gcts)) + ' |\n')
        file_ptr.write('| --- | ' + ' | '.join(('---' for _ in gcts)) + ' |\n')
        for k in sorted(XGC_ENTRY_SCHEMA.keys()):
            file_ptr.write(f'| {k} | ' + ' | '.join((md_string(gct, k) for gct in gcts)) + ' |\n')
