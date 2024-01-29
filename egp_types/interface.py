"""The interface module.

# Interfaces

An interface is defined by the interface class which is derived from the python array class.
An interface has a list of endpoints with 0 to 256 elements.
Endpoints in the interface may be connected as source or destination endpoints.
There are two specialisations of the interface class: source_interface and destination_interface.

# Source Interfaces

A source interface is defined by the source_interface class which is derived from the interface class.
Source interfaces can only have connections to destination interfaces.

# Destination Interfaces

A destination interface is defined by the destination_interface class which is derived from the interface class.
Destination interfaces can only have connections from source interfaces.
"""
from __future__ import annotations
from array import array
from typing import Iterable
from logging import getLogger, Logger, NullHandler
from .ep_type import validate
from .egp_typing import EndPointType


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())


class interface(array):
    """An interface is a node in the genomic library."""

    def __init__(self, _: Iterable[EndPointType]) -> None:
        pass

    def __new__(cls, val: Iterable[EndPointType]):
        return super().__new__(cls, 'h', val)  # type: ignore

    def assertions(self) -> None:
        """Validate assertions for the interface."""
        if len(self) > 256:
            raise ValueError("interface has too many endpoints")
        for idx, ept in enumerate(self):
            if not validate(ept):
                raise ValueError(f"endpoint {idx} does not have a valid egp_type: {ept}")


class empty_interface(interface):
    """An empty interface is an interface with no endpoints."""

    def __init__(self) -> None:
        pass

    def __new__(cls):
        return super().__new__(cls, [])

    def __setitem__(self, _, __) -> None:
        assert False, "empty_interface cannot be modified"

    def append(self, _) -> None:
        """Cannot append to an empty interface."""
        assert False, "empty_interface cannot be modified"

    def extend(self, _) -> None:
        """Cannot extend an empty interface."""
        assert False, "empty_interface cannot be modified"

    def insert(self, _, __) -> None:
        """Cannot insert into an empty interface."""
        assert False, "empty_interface cannot be modified"


class src_interface(interface):
    """A source interface is an interface that can only have connections to destination interfaces."""


class dst_interface(interface):
    """A destination interface is an interface that can only have connections from source interfaces."""


EMPTY_INTERFACE = empty_interface()
