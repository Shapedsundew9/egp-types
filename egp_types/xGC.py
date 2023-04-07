" The xGC type."
from typing import Literal
from logging import DEBUG, Logger, NullHandler, getLogger
from egp_utils.packed_store import entry


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# If this field exists and is not None the gGC is a pGC
_PROOF_OF_PGC: Literal['pgc_fitness'] = 'pgc_fitness'


class xGC(entry):
    """xGC is an entry in the GPC."""

    def is_pgc(self) -> bool:
        """True if the xGC is a pGC."""
        return _PROOF_OF_PGC in self


# gGC is an alias of xGC
gGC = xGC
