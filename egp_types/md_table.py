from .eGC import eGC
from .xgc_validator import XGC_ENTRY_SCHEMA
from typing import Literal


# GitHub Markdown Emoji's
_DEFINABLE_MD: Literal[':large_blue_circle:'] = ":large_blue_circle:"
_REQUIRED_MD: Literal[':black_circle:'] = ":black_circle:"


def md_string(gct, key) -> Literal['', ':large_blue_circle:', ':black_circle:']:
    """Generate the GitHub MD string relevant to the key for gct."""
    if key not in gct.validator.schema:
        return ""
    if 'default' in gct.validator.schema[key] or 'default_setter' in gct.validator.schema[key]:
        return _DEFINABLE_MD
    return _REQUIRED_MD


def md_table() -> None:
    """Create a GitHub Markdown table showing the requirements of each field for each GC type."""
    gcts: tuple[eGC] = (
        eGC(),
    )
    with open('gc_type_table.md', 'w') as file_ptr:
        file_ptr.write("GC Type Field Requirements\n")
        file_ptr.write("==========================\n\n")
        file_ptr.write(_DEFINABLE_MD + ': Defined if not set, ' + _REQUIRED_MD + ': Required.\n\n')
        file_ptr.write('| Field | ' + ' | '.join((x.__class__.__qualname__ for x in gcts)) + ' |\n')
        file_ptr.write('| --- | ' + ' | '.join(('---' for _ in gcts)) + ' |\n')
        for k in sorted(XGC_ENTRY_SCHEMA.keys()):
            file_ptr.write(f'| {k} | ' + ' | '.join((md_string(gct, k) for gct in gcts)) + ' |\n')
