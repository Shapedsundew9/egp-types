"""The interface module.

# Interfaces

An interface is defined by the interface class which is derived from the numpy ndarray class.
An interface has an array of endpoints with 0 to 256 elements.
Endpoints in the interface may be connected as source and/or destination endpoints.
See connections class for more details.
There are two specialisations of the interface class: source_interface and destination_interface.

# Source Interfaces

A source interface is defined by the src_interface class which is derived from the interface class.
Source interfaces can only have connections to destination interfaces.

# Destination Interfaces

A destination interface is defined by the dst_interface class which is derived from the interface class.
Destination interfaces can only have connections from source interfaces.
"""
from __future__ import annotations

from logging import Logger, NullHandler, getLogger
from typing import cast, Literal

from numpy import int16, ndarray

from .egp_typing import ConstantExecStr, EndPointType, Row, EndPointClassStr
from .ep_type import ep_type_lookup, validate, asstr


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())


class interface(ndarray):
    """An interface is a node in the genomic library."""

    def __init__(self, val: list[EndPointType]) -> None:
        self[:] = val

    def __new__(cls, val: list[EndPointType]) -> interface:
        return super().__new__(cls, len(val), dtype=int16)  # pylint: disable=unexpected-keyword-arg

    def __repr__(self) -> str:
        """Return the string representation of the interface."""
        return f"Interface instance: {id(self)}\n\t" + "\n\t".join(f"{i}: {asstr(val)} ({val})" for i, val in enumerate(self))

    def mermaid(self, row:Row, cls:EndPointClassStr) -> list[str]:
        """Return the mermaid charts string for the source interface.
        e.g. uidA001d["A001d: 1"]"""
        endpoints: list[str] = [f'\tuid{row}{idx:03}{cls}["{row}{idx:03}{cls}: {ept}"]' for idx, ept in enumerate(self)]
        return[f"subgraph uid{row}{cls}", "\tdirection TB"] + endpoints + ["end"]

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
        super().__init__([])

    def __new__(cls) -> empty_interface:
        return cast(empty_interface, super().__new__(cls, []))

    def __setitem__(self, _, value) -> None:
        assert not value, "empty_interface cannot be modified"

    def mermaid(self, _: Row, __: Literal["s", "d"] = "s") -> list[str]:
        """Mermaid charts string is empty for an empty interface."""
        return []

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

    def mermaid(self, row:Row, cls: Literal["s"] = "s") -> list[str]:
        """Return the mermaid charts string for the source interface.
        e.g. A001s["A001s: 1"]"""
        return super().mermaid(row, cls)

class dst_interface(interface):
    """A destination interface is an interface that can only have connections from source interfaces."""

    def mermaid(self, row:Row, cls: Literal["d"] = "d") -> list[str]:
        """Return the mermaid charts string for the source interface.
        e.g. A001d["A001d: 1"]"""
        return super().mermaid(row, cls)


# Used as a default value: Referencing the same object saves space and time.
EMPTY_INTERFACE = empty_interface()


class interface_c(src_interface):
    """A constant is a source interface with a string member that defines its value as executable code."""

    __slots__: list[str] = ["value"]

    def __init__(self, values: list[ConstantExecStr], types: list[EndPointType]) -> None:
        """Initialize a constants row from a list of values and a list of endpoint types."""
        super().__init__(types)
        self.values: list[str] = values

    def __new__(cls, values: list[ConstantExecStr], types: list[EndPointType]) -> interface_c:
        """Create a constants row from a list of values and a list of endpoint types."""
        return cast(interface_c, super().__new__(cls, types))


class interface_f(dst_interface):
    """Row F is a specialization of the dst_interface. Row F can only have a single endpoint of type bool."""

    def __init__(self) -> None:
        """No initialization required."""
        super().__init__([ep_type_lookup["n2v"]["bool"]])

    def __new__(cls) -> interface_f:
        """Construct a row F."""
        return cast(interface_f, super().__new__(cls, [ep_type_lookup["n2v"]["bool"]]))


# Used as a default values: Referencing the same object saves space and time.
EMPTY_INTERFACE_C = interface_c([], [])
INTERFACE_F = interface_f()
EMPTY_IO: tuple[empty_interface, empty_interface] = (EMPTY_INTERFACE, EMPTY_INTERFACE)
