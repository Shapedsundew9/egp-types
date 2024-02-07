"""
Terminal Genetic Code module.

A terminal genetic code is a genetic code that has no defined sub-GC's in the gene pool cache (gca, gcb).
The sub-GCs are stored in the genomic library and are loaded as required.
"""

from __future__ import annotations

from logging import DEBUG, Logger, NullHandler, getLogger

from .genetic_code import genetic_code

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


class terminal_genetic_code(genetic_code):
    """A leaf node in the Gene Pool Cache graph that is *NOT* a codon."""

    def __init__(self, gc: genetic_code) -> None:
        """A terminal genetic code subsumes the data of the genetic code that forms it."""
        self.idx: int = gc.idx
        self["objects"] = self

    def assertions(self) -> None:
        """Validate assertions for the genetic code."""
        super().assertions()
