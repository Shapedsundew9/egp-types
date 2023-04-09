" The xGC type."
from __future__ import annotations
from typing import Literal, TypeGuard, Any
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

    def is_pgc(self, _: Any = None) -> TypeGuard[pGC]:
        """True if the xGC is a pGC."""
        # TODO: This needs to be a lot more definitive. The common case needs to be quick.
        return _PROOF_OF_PGC in self

    def is_ggc(self, _: Any = None) -> TypeGuard[gGC]:
        """True if the xGC is a gGC."""
        # TODO: This should not be 'not pGC' but what is required to be a gGC. There are
        # semantically the same but the latter may catch bugs.
        return _PROOF_OF_PGC not in self

    def to_pgc(self) -> pGC:
        """Cast the xGC to pGC."""
        if self.is_pgc():
            self.__class__ = pGC
            return self  # type: ignore
        raise RuntimeError('xGC cast to pGC but does not meet constraints to do so.')

    def to_ggc(self) -> gGC:
        """Cast the xGC to gGC."""
        if self.is_ggc():
            self.__class__ = gGC
            return self  # type: ignore
        raise RuntimeError('xGC cast to gGC but does not meet constraints to do so.')


class pGC(xGC):
    """pGC is a specialization of xGC."""
    # NOTE: pGC cannot define any new members, only methods, to support xGC light weight cast.


class gGC(xGC):
    """gGC is a specialization of xGC."""
    # NOTE: pGC cannot define any new members, only methods, to support xGC light weight cast.
