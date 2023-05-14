"""All the GC types as a superset type."""
from .dGC import dGC
from .eGC import eGC
from .xGC import xGC

aGC = dGC | eGC | xGC
