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
        self.empty_indices: list[int] = [0]
        self.size: int = size
        self._remaining: bool = True
        self.purge: Callable[[list[int]], None] = purge
        self.purged_object: object = purged_object

    def __getitem__(self, idx: int) -> object:
        """Return the object at the specified index."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        raise NotImplementedError

    def reset(self, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self.empty_indices: list[int] = [0]
        self.size: int = size if size is not None else self.size
        self._remaining: bool = True

    def _purge(self, fraction: float = 0.25) -> list[int]:
        """Purge the store of unused data."""
        raise NotImplementedError

    def next_index(self) -> int:
        """Return the next index for a new node."""
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
            next_index = self.empty_indices[0]
            self.empty_indices[0] += 1
            self._remaining = self.empty_indices[0] < (self.size - 1)
        return next_index

    def assertions(self) -> None:
        """Validate assertions for the store."""
        assert len(self.empty_indices) <= self.size
        if self._remaining:
            assert self.empty_indices[0] < self.size


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

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        if self._remaining:
            return self.empty_indices[0]
        return self.size - len(self.empty_indices)
    

class dynamic_store(store):
    """A memory efficient store that grows as needed with block allocation.

    Data is stored in a list of arrays and indexed.
    It is the responsibility of the calling class to use the right index.
    The index is a single integer value that is masked to create a block index
    and a block offset. The block index is used to access the correct block
    and the block offset is used to access the correct element in the block.
    When all the existing blocks are full a new block is added to the list.
    A purge method is provided to remove old data.
    """

    def __init__(self, logsize: int = DEFAULT_DYNAMIC_STORE_LOGSIZE, purged_object: object = None, purge: Callable[[list[int]], None] = lambda x: None) -> None:
        """Initialize the store."""
        super().__init__(logsize, purged_object, purge)
        self.objects: NDArray[Any] = empty(self.size, dtype=object)
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)

    def __getitem__(self, idx: int) -> genetic_code:
        """Return the object at the specified index."""
        return self.objects[idx]

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        if self._remaining:
            return self.empty_indices[0]
        return self.size - len(self.empty_indices)

    def reset(self, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self.empty_indices: list[int] = [0]
        self.size: int = size if size is not None else self.size
        self._remaining: bool = True

        # Stored data
        # 8 bytes per element
        self.objects: NDArray[Any] = empty(self.size, dtype=object)
        # 8 bytes per element
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)
        # Total bytes = 16 * size

    def _purge(self, fraction: float = 0.25) -> list[int]:
        """Purge the store of unused data."""
        # Simply marking the data as unused is insufficient because the purged
        # data may be referenced by other objects. The purge function ensures that
        # all references to the purged data in the store are removed.
        assert not self.empty_indices, "empty_indices is not empty"
        num_to_purge: int = int(self.size * fraction)
        _logger.info(f"Purging {int(100*fraction)}% = ({num_to_purge} of {self.size}) of the store")
        purge_indices: list[int] = argsort(self.access_sequence)[:num_to_purge].tolist()

        # Do what is necessary with the doomed objects before they are purged
        self.purge(purge_indices)

        # Remove any references to the purged objects
        for idx in purge_indices:
            self.objects[idx] = self.purged_object

        # Clean up the heap
        _logger.debug(f"{collect()} unreachable objects not collected after purge.")
        return purge_indices

    def assign_index(self, obj: object) -> int:
        """Return the next index for a new node."""
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
            next_index = self.empty_indices[0]
            self.empty_indices[0] += 1
            self._remaining = self.empty_indices[0] < (self.size - 1)
        # Assign the object to the next index and return the index
        self.objects[next_index] = obj
        return next_index

    def assertions(self) -> None:
        """Validate assertions for the store."""
        assert len(self.objects) == self.size
        assert len(self.access_sequence) == self.size
        assert len(self.empty_indices) <= self.size
        if self._remaining:
            assert self.empty_indices[0] < self.size


class gene_pool_cache(static_store):
    """A memory efficient store genetic codes."""

    # The global genomic library
    # Is used in nodes for lazy loading of dependent nodes
    gl: genomic_library = genomic_library()

    def __init__(self, size: int = DEFAULT_STATIC_STORE_SIZE, purged_object: object = None, purge: Callable[[list[int]], None] = lambda x: None) -> None:
        """Initialize the storage."""
        super().__init__(size, purged_object, purge)
        self.genetic_code: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.gca: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.gcb: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.graph: NDArray[Any] = empty(self.size, dtype=graph)
        self.ancestor_a: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.ancestor_b: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.descendants: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)

    def __getitem__(self, idx: int) -> _genetic_code:
        """Return the object at the specified index."""
        return self.genetic_code[idx]

    def __delitem__(self, idx: int) -> None:
        """Remove the object at the specified index."""
        #TODO: Push to genomic library
        self.genetic_code[idx] = self.purged_object
        self.empty_indices.append(idx)

    def reset(self, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        super().reset(size)
        self.genetic_code: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.gca: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.gcb: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.graph: NDArray[Any] = empty(self.size, dtype=graph)
        self.ancestor_a: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.ancestor_b: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.descendants: NDArray[Any] = empty(self.size, dtype=_genetic_code)
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)
        # Total = 8 * 8 = 64 bytes + base class per element

    def _purge(self, fraction: float = 0.25) -> list[int]:
        """Purge the store of unused data."""
        # Simply marking the data as unused is insufficient because the purged
        # data may be referenced by other objects. The purge function ensures that
        # all references to the purged data in the store are removed.
        assert not self.empty_indices, "empty_indices is not empty"
        num_to_purge: int = int(self.size * fraction)
        _logger.info(f"Purging {int(100*fraction)}% = ({num_to_purge} of {self.size}) of the store")
        purge_indices: list[int] = argsort(self.access_sequence)[:num_to_purge].tolist()

        # Do what is necessary with the doomed objects before they are purged
        self.purge(purge_indices)

        # Remove any references to the purged objects
        for idx in purge_indices:
            self.objects[idx] = self.purged_object

        # Clean up the heap
        _logger.debug(f"{collect()} unreachable objects not collected after purge.")
        return purge_indices

