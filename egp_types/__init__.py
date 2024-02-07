"""Initialization for the package."""
from ._genetic_code import _genetic_code, GPC_DEFAULT_SIZE
from .store import static_store


# Define the storage for the genetic code data
_genetic_code.gene_pool_cache = static_store(GPC_DEFAULT_SIZE)
