"""Common Erasmus GP Types."""
from typing import Callable, Iterable
from .xGC import xGC


FitnessFunction = Callable[[Iterable[xGC]], None]
SurvivabilityFunction = Callable[[Iterable[xGC], Iterable[xGC]], None]
