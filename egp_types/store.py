"""Data store for genetic_codes."""
from __future__ import annotations

from gc import collect
from logging import DEBUG, Logger, NullHandler, getLogger
from typing import Any, TYPE_CHECKING, Callable

from egp_stores.genomic_library import genomic_library
from numpy import argsort, empty, int64, intp, int8
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .genetic_code import _genetic_code
    from .graph import graph

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


# Constants
DEFAULT_STATIC_STORE_SIZE: int = 2**16
# For a dynamic store consider what overhead is tolerable. For a python int that could be stored in 4 bytes
# the overhead is ~24 bytes. To reduce this to ~1% using a numpy array (overhead 112 bytes) the store size
# would need to be ~2**13 bytes or 2**11 4 byte integers. This is a reasonable size for a dynamic store.
DEFAULT_DYNAMIC_STORE_LOGSIZE: int = 11


class store:
    """A memory efficient store for numeric data.

    Data is stored in public members as arrays and indexed.
    It is the responsibility of the calling class to use the right index.
    The class provides a method for returning the next free index
    and marking an index as free.
    When the store is full, the purge method is called to purge unused data.
    The purge method calls the supplied user defined purge function to return
    a list of indices to be purged.
    """

    def __init__(self, size: int, purged_object: object, purge: Callable[[list[int]], None]) -> None:
        """Initialize the store.
        
        empty_indices: Is a list of empty indices in the store when _remaining is False
        size: The size of the store.
        _remaining: Is True if the store has not yet been filled once. In this case
            empty_indices[0] is the number of empty indices until full.
        purged_object: An object to use to replace purged objects.
        """
        self.empty_indices: list[int] = []
        self.size: int = size
        self._remaining: int = size
        self.purge: Callable[[list[int]], None] = purge
        self.purged_object: object = purged_object

    def __delitem__(self, idx: int) -> None:
        """Remove the object at the specified index."""
        raise NotImplementedError
    
    def __getitem__(self, idx) -> Any:
        """Return the object at the specified index."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        raise NotImplementedError

    def reset(self, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self.empty_indices: list[int] = []
        self.size: int = size if size is not None else self.size
        self._remaining: int = self.size

    def _purge(self, fraction: float = 0.25) -> list[int]:
        """Purge the store of unused data."""
        raise NotImplementedError

    def next_index(self) -> int:
        """Return the next index for a new node."""
        raise NotImplementedError

    def assertions(self) -> None:
        """Validate assertions for the store."""
        assert len(self.empty_indices) <= self.size
        if self._remaining:
            assert not self.empty_indices


class static_store(store):
    """A memory efficient store for numeric data.

    Data is stored in public members as arrays and indexed.
    It is the responsibility of the calling class to use the right index.
    The class provides a method for returning the next free index
    and marking an index as free.
    When the store is full, the purge method is called to purge unused data.
    The purge method calls the supplied user defined purge function to return
    a list of indices to be purged.
    """

    def __init__(self, size: int = DEFAULT_STATIC_STORE_SIZE, purged_object: object = None, purge: Callable[[list[int]], None] = lambda x: None) -> None:
        """Initialize the store.
        
        empty_indices: Is a list of empty indices in the store when _remaining is False
        size: The size of the store.
        _remaining: Is True if the store has not yet been filled once. In this case
            empty_indices[0] is the number of empty indices until full.
        purged_object: An object to use to replace purged objects.
        """
        super().__init__(size, purged_object, purge)

    def __delitem__(self, idx: int) -> None:
        """Remove the object at the specified index."""
        raise NotImplementedError

    def __getitem__(self, idx) -> Any:
        """Return the object at the specified index."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        if self._remaining:
            return self.size - self._remaining
        return self.size - len(self.empty_indices)

    def next_index(self) -> int:
        # Whilst initially filling the store the first (and only) element
        # of self.empty_indices is the next index. Once the store is full
        # self.empty_indices is a list of indices that are free.
        next_index: int
        if not self._remaining:
            if not self.empty_indices:
                # In the event the store is full the purge method is called.
                self.empty_indices = self._purge()
            next_index = self.empty_indices.pop(0)
        else:
            next_index = self.size - self._remaining
            self._remaining -= 1
        return next_index

    def _purge(self, fraction: float = 0.25) -> list[int]:
        """Purge the store of unused data."""
        return []


class dynamic_store(store):
    """A dynamic store is an extensible (and retractable) list of static stores."""

    def __init__(self, size: int = DEFAULT_DYNAMIC_STORE_LOGSIZE, purged_object: object = None) -> None:
        """Initialize the store."""
        super().__init__(2**size, purged_object, lambda x: None)
        self._size: int = size
        self._mask: int = 2**size - 1
        self._stores: list[static_store] = []
        self._add_store()
        self._store_idx: int = 0
        self.num_elements: int = 0

    def __delitem__(self, idx: int) -> None:
        """Remove the object at the specified index."""
        del self._stores[idx >> self._size][idx & self._mask]

    def __getitem__(self, member: str) -> Any:
        """Return the object at the specified index."""
        return self._stores[idx >> self._size][idx & self._mask]

    def __len__(self) -> int:
        """The length of the store is the sum of the lengths of the static stores."""
        return sum(len(store) for store in self._stores)

    def _add_store(self) -> None:
        """Add a new static store to the dynamic store."""
        self._stores.append(static_store(2**self._size, self.purged_object, self.purge))

    def allocation(self) -> int:
        """Return the total space allocated in objects."""
        return len(self._stores) * 2**self.size

    def next_index(self) -> int:
        """Return the next index for a new node."""
        # If there are any empty indices then return the first one.
        if not self.empty_indices:
            return self.empty_indices.pop(0)

        # Else get the next index from the current store. If the store is full after
        # getting the index (i.e. the index is the store size - 1) then add a new
        # store to the dynamic store.
        idx: int = self._stores[self._store_idx].next_index()
        ret_idx: int = idx + (self._store_idx << self._size)
        if idx == self._mask:
            self._store_idx += 1
            self._add_store()
        return ret_idx
