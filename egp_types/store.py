"""Generic compact data store.



"""
from __future__ import annotations

from gc import collect
from logging import DEBUG, Logger, NullHandler, getLogger
from typing import Any, TYPE_CHECKING, Self

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
# For a dynamic store consider what overhead is tolerable. For a python int that could be stored in 4 bytes
# the overhead is ~24 bytes. To reduce this to ~1% using a numpy array (overhead 112 bytes) the store size
# would need to be ~2**13 bytes or 2**11 4 byte integers. This is a reasonable size for a dynamic store.
DDSL: int = 11
DSSS: int = 2**DDSL


class store:
    """A memory efficient store for numeric data."""

    def __init__(self, size: int) -> None:
        """Initialize the store."""
        self._empty_indices: list[int] = []
        self._size: int = size
        self._remaining: int = self._size
        self._last_index = -1

    def __delitem__(self, idx: int) -> None:
        """Remove the object at the specified index."""
        raise NotImplementedError

    def __getitem__(self, idx) -> Any:
        """Return the object at the specified index."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Return the number of occupied entries."""
        if self._remaining:
            return self._size - self._remaining
        return self._size - len(self._empty_indices)

    def __setitem__(self, idx, val) -> Any:
        """Set the object at the specified index."""
        raise NotImplementedError

    def assertions(self) -> None:
        """Validate assertions for the store."""
        assert len(self._empty_indices) <= self._size
        if self._remaining:
            assert not self._empty_indices

    def clone(self) -> Self:
        """Return a clone of the store. i.e. same parameters but uninitialized data."""
        return type(self)(self._size)

    def empty_indices(self) -> list[int]:
        """Return the empty indices."""
        return list(range(len(self), self._size)) if self._remaining else self._empty_indices

    def last_index(self) -> int:
        """Return the last index used."""
        return self._last_index

    def next_index(self) -> int:
        """Return an available index. If none are available -1 is returned."""
        if self._remaining:
            self._remaining -= 1
            self._last_index: int = self._size - self._remaining - 1
            return self._last_index
        if self._empty_indices:
            self._last_index = self._empty_indices.pop(0)
            return self._last_index
        raise OverflowError("No more space available.")

    def reset(self, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self._empty_indices: list[int] = []
        self._size: int = size if size is not None else self._size
        self._remaining: int = self._size

    def size(self) -> int:
        """Return the size of the store."""
        return self._size
    
    def space(self) -> int:
        """Return the space remaining in the store."""
        return self._size - len(self)


class static_store_member():
    """An indexing object for static stores if indexing is not directly supported."""

    def __init__(self, _store: static_store, member: str) -> None:
        self._member: str = member
        self._store: static_store = _store

    def __delitem__(self, _: int) -> None:
        """Removing a member element is not supported."""
        raise RuntimeError("The dynamic store does not support deleting members.")

    def __getitem__(self, idx: int) -> Any:
        """Return the object at the specified index."""
        return self._store[self._member][idx]

    def __setitem__(self, idx: int, val: Any) -> None:
        """Set the object at the specified index."""
        self._store[self._member][idx] = val


class static_store(store):
    """A memory efficient store."""

    def __init__(self, size: int = DSSS) -> None:
        """Initialize the store."""
        super().__init__(size)
        # members: list[str] = [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith("_")]
        # self._members: dict[str, static_store_member] = {m: static_store_member(self, m) for m in members}

    def __delitem__(self, idx: int) -> None:
        """Mark the specified index empty."""
        self._empty_indices.append(idx)

    def __getitem__(self, member: str) -> Any:
        """Return the specified member."""
        return getattr(self, member)

    def __setitem__(self, member: str, val: Any) -> None:
        """Set the member at the last index returned by self.next_index()"""
        getattr(self, member)[self._last_index] = val


class _dynamic_store_member():
    """An indexing object for dynamic stores."""
    _stores: list[static_store]
    _log2size: int
    _mask: int

    def __init__(self, member: str) -> None:
        self._member: str = member

    def __delitem__(self, _: int) -> None:
        """Removing a member element is not supported."""
        raise RuntimeError("The dynamic store does not support deleting member elements.")

    def __getitem__(self, idx: int) -> Any:
        """Return the object at the specified index."""
        cls = type(self)
        return cls._stores[idx >> cls._log2size][self._member][idx & cls._mask]

    def __setitem__(self, idx: int, val: Any) -> None:
        """Set the object at the specified index creating a new store if required."""
        cls = type(self)
        store_idx: int = idx >> self._log2size
        if store_idx >= len(cls._stores):
            for _ in range(store_idx - len(cls._stores) + 1):
                cls._stores.append(cls._stores[0].clone())
        cls._stores[store_idx][self._member][idx & cls._mask] = val


class dynamic_store(store):
    """A dynamic store is an extensible (and retractable) list of static stores.
    TODO: Implement retraction.
    """

    # Used to ensure dynamically created member classes are uniquely named per instance.
    ds_member_cls_idx: int = 0

    def __init__(self, store_t: type[static_store], log2size: int = DDSL) -> None:
        """Initialize the store."""
        super().__init__(2**log2size)
        self._store_t: type[static_store] = store_t
        self._log2size: int = log2size
        super().reset(2**self._log2size)
        self._stores = [self._store_t(2**self._log2size)]
        self._store_idx = 0
        self._mask: int = 2**self._log2size - 1
        self._store_idx: int = 0
        self._stores: list[static_store] = []
        self._stores.append(self._store_t(2**self._log2size))

        # Dynamically create a derived class of _dynamic_store_member with the dynamic_store parameters set.
        ds_member_cls = type(f"ds_member_cls_{dynamic_store.ds_member_cls_idx}", (_dynamic_store_member, ), {})
        dynamic_store.ds_member_cls_idx += 1
        ds_member_cls._stores = self._stores
        ds_member_cls._log2size = self._log2size
        ds_member_cls._mask = self._mask

        # Create a member index wrapper for each member. Must instance the store to see the attributes.
        _store_t: static_store = store_t(0)
        members: list[str] = [attr for attr in dir(_store_t) if not callable(getattr(_store_t, attr)) and not attr.startswith("_")]
        self.members: dict[str, ds_member_cls] = {member: ds_member_cls(member) for member in members}

    def __delitem__(self, idx: int) -> None:
        """Remove the specified index."""
        del self._stores[idx >> self._log2size][idx & self._mask]

    def __getitem__(self, member: str) -> Any:
        """Return the specified member."""
        return self.members[member]

    def __len__(self) -> int:
        """The length of the store is the sum of the lengths of the static stores."""
        return sum(len(store) for store in self._stores)

    def __setitem__(self, member: str, val: Any) -> None:
        """Set the member at the last index returned by self.next_index()"""
        self.members[member][self._last_index] = val

    def allocation(self) -> int:
        """Return the total space allocated in objects."""
        return len(self._stores) * 2**self._log2size

    def empty_indices(self) -> list[int]:
        """Return the empty indices."""
        return [(si << self._log2size) + idx for si, s in enumerate(self._stores) for idx in s.empty_indices()]

    def next_index(self) -> int:
        """Return the next index for a new node."""
        for store_idx, _store in enumerate(self._stores):
            if _store.space():
                self._last_index = _store.next_index() + (store_idx << self._log2size)
                return self._last_index

        # Run out of space in the existing stores. Create a new store.
        self._store_idx = len(self._stores)
        self._stores.append(self._stores[0].clone())
        self._last_index = self._stores[self._store_idx].next_index() + (self._store_idx << self._log2size)
        return self._last_index

    def reset(self, size: int | None = None) -> None:
        """A full reset of the store allows the size to be changed. All genetic codes
        are deleted which pushes the genetic codes to the genomic library as required."""
        self._log2size: int = size if size is not None else self._log2size
        super().reset(2**self._log2size)
        self._stores = [self._store_t(2**self._log2size)]
        self._store_idx = 0
        self._mask: int = 2**self._log2size - 1
        self._store_idx: int = 0
        self._stores: list[static_store] = []
        self._stores.append(self._store_t(2**self._log2size))

    def size(self) -> int:
        """Return the size of the store."""
        return len(self._stores) * 2**self._log2size

    def space(self) -> int:
        """Return the space remaining in the store."""
        return 2**63 - 1  # Infinite space.
