" The xGC type."
from typing import Any, NoReturn, TypedDict, Literal, Generator, Self
from logging import DEBUG, Logger, NullHandler, getLogger
from collections.abc import KeysView as dict_keys


class Field(TypedDict):
    """GPC configured field definition."""

    type: Any
    length: int
    default: Any
    read_only: bool
    read_count: int
    write_count: int


# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# If this field exists and is not None the gGC is a pGC
_PROOF_OF_PGC: Literal['pgc_fitness'] = 'pgc_fitness'


class xGC():
    """xGC is a dict-like object."""

    def __init__(self, _data: dict[str, list[Any]], allocation: int, idx: int, fields: dict[str, Field]) -> None:
        """xGC is a dict-like object with some specialisations for the GPC.

        Args
        ----
        _data: Is the _gpc from which individual GC's are read & written.
        allocation: Is the index of the allocation in the store for this GC.
        idx: Is the index in the allocation.
        fields: The definition of the fields in the xGC
        """
        self._data: dict[str, list[Any]] = _data
        self._allocation: int = allocation
        self._idx: int = idx
        self.fields: dict[str, Field] = fields

    def __contains__(self, key: str) -> bool:
        """Checks if key is one of the fields in xGC."""
        return key in self.fields

    def __getitem__(self, key: str) -> Any:
        """Return the value stored with key."""
        if __debug__:
            assert key in self.fields, f"{key} is not a key in data. Are you trying to get a pGC field from a gGC?"
            self.fields[key]['read_count'] += 1
            _logger.debug(f"Getting GGC key '{key}' from allocation {self._allocation}, index {self._idx}).")
        return self._data[key][self._allocation][self._idx]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set the value stored with key."""
        if __debug__:
            assert key in self._data, f"'{key}' is not a key in data. Are you trying to set a pGC field in a gGC?"
            assert not self.fields[key]['read_only'], f"Writing to read-only field '{key}'."
            self.fields[key]['write_count'] += 1
            _logger.debug(f"Setting GGC key '{key}' to allocation {self._allocation}, index {self._idx}).")
        self._data[key][self._allocation][self._idx] = value
        self._data['__modified__'][self._allocation][self._idx] = True

    def __copy__(self) -> NoReturn:
        """Make sure we do not copy gGCs. This is for performance."""
        assert False, f"Shallow copy of xGC ref {self['ref']:016X}."

    def __deepcopy__(self, obj: Self) -> NoReturn:
        """Make sure we do not copy gGCs. This is for performance."""
        assert False, f"Deep copy of xGC ref {self['ref']:016X}."

    def keys(self) -> dict_keys[str]:
        """A view of the keys in the xGC."""
        return self._data.keys()

    def is_pgc(self) -> bool:
        """True if the xGC is a pGC."""
        return _PROOF_OF_PGC in self._data

    def items(self) -> Generator[tuple[str, Any], None, None]:
        """A view of the xGCs in the GPC."""
        for key in self._data.keys():
            yield key, self[key]

    def update(self, value: dict | Self) -> None:
        """Update the xGC with a dict-like collection of fields."""
        for k, v in value.items():
            self[k] = v

    def values(self) -> Generator[Any, None, None]:
        """A view of the field values in the xGC."""
        for key in self._data.keys():
            yield self[key]
