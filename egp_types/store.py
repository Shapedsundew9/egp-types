"""Data store for genetic_codes."""
from __future__ import annotations

from gc import collect
from logging import DEBUG, Logger, NullHandler, getLogger
from typing import Any, TYPE_CHECKING, Callable

from egp_stores.genomic_library import genomic_library
from numpy import argsort, empty, int64, intp, int8
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .genetic_code import genetic_code

# Logging
_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)


DEFAULT_STORE_SIZE: int = 2**16


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

    def __init__(self, size: int = DEFAULT_STORE_SIZE, purged_object: object = None, purge: Callable[[list[int]], None] = lambda x: None) -> None:
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


class gene_pool_cache(store):
    """A memory efficient store genetic codes."""

    # The global genomic library
    # Is used in nodes for lazy loading of dependent nodes
    gl: genomic_library = genomic_library()

    def __init__(self, size: int = DEFAULT_STORE_SIZE) -> None:
        """Initialize the store.
        
        empty_indices: Is a list of empty indices in the store when _remaining is False
        size: The size of the store.
        _remaining: Is True if the store has not yet been filled once. In this case
            empty_indices[0] is the number of empty indices until full.
        purged_object: An object to use to replace purged objects.
        genetic_codes: The genetic codes in the store.
        access_sequence: When a genetic code is 'touched' the access number is
            updated to the next access number. This is used to implement an LRU policy.
        state: The storage state of the genetic code. Different states have different
            storage requirements.
                    0: The genetic code was created in the current runtime.
                    1: The genetic code was loaded from the genomic library.
                    2: The genetic code is terminal i.e. edges connect to purged genetic codes.
        """
        self.empty_indices: list[int] = [0]
        self.size: int = size
        self._remaining: bool = True
        self.purged_object: object = object()
        self.genetic_codes: NDArray[Any] = empty(self.size, dtype=object)
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)
        self.state: NDArray[Any] = empty(self.size, dtype=int8)

        # Genetic code data
        self.gca: NDArray[Any] = empty(self.size, dtype=object)
        self.gcb: NDArray[Any] = empty(self.size, dtype=object)
        self.graph: NDArray[Any] = empty(self.size, dtype=object)
        self.ancestor_a: NDArray[Any] = empty(self.size, dtype=object)
        self.ancestor_b: NDArray[Any] = empty(self.size, dtype=object)
        self.descendants: NDArray[Any] = empty(self.size, dtype=object)

    def __getitem__(self, idx: int) -> genetic_code:
        """Return the object at the specified index."""
        return self.genetic_codes[idx]

    def __len__(self) -> int:
        """Return the number of nodes in the genomic library."""
        if self._remaining:
            return self.empty_indices[0]
        return self.size - len(self.empty_indices)

    def reset(self, size: int = DEFAULT_STORE_SIZE) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self.empty_indices: list[int] = [0]
        self.size: int = size
        self._remaining: bool = True

        # Stored data
        # 8 bytes per element
        self.genetic_codes: NDArray[Any] = empty(self.size, dtype=object)
        # 8 bytes per element
        self.access_sequence: NDArray[int64] = empty(self.size, dtype=int64)
        # Total bytes = 16 * size

    def _purge(self) -> list[int]:
        """Purge the store of unused data."""
        # Simply marking the data as unused is insufficient because the purged
        # data may be referenced by other objects. The purge function ensures that
        # all references to the purged data in the store are removed.
        assert not self.empty_indices, "empty_indices is not empty"
        num_to_purge: int = self.size // 4
        _logger.info(f"Purging 25% ({num_to_purge} of {self.size}) of the store")
        purged: NDArray[intp] = argsort(self.access_sequence)[:num_to_purge]
        doomed_objects: set[Any] = {self.genetic_codes[int(idx)] for idx in purged}

        # Push doomed objects to the global genomic library if they have value
        # TODO

        # Remove any references to the purged objects
        for idx, obj in enumerate(self.genetic_codes):
            # Objects must be _genetic_code instances
            obj.purge(doomed_objects)
            if obj in doomed_objects:
                self.genetic_codes[idx] = self.purged_object

        # Clean up the heap
        _logger.debug(f"{collect()} unreachable objects not collected after purge.")
        return purged.tolist()

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
        self.genetic_codes[next_index] = obj
        return next_index

    def assertions(self) -> None:
        """Validate assertions for the store."""
        assert len(self.genetic_codes) == self.size
        assert len(self.access_sequence) == self.size
        assert len(self.empty_indices) <= self.size
        if self._remaining:
            assert self.empty_indices[0] < self.size
            for idx in range(self.empty_indices[0]):
                self.genetic_codes[idx].assertions()
        else:
            for idx, obj in enumerate(self.genetic_codes):
                obj.assertions()
