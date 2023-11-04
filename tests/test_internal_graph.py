"""Test cases for the internal graph module."""
from json import dump, load
from logging import DEBUG, INFO, Logger, NullHandler, getLogger
from os.path import dirname, exists, join
from tqdm import trange

from egp_types.graph_validators import limited_igraph_validator as liv
from egp_types.internal_graph import internal_graph, random_internal_graph


_logger: Logger = getLogger(__name__)
_logger.addHandler(NullHandler())
_LOG_DEBUG: bool = _logger.isEnabledFor(DEBUG)
getLogger("surebrec").setLevel(INFO)
getLogger("eGC").setLevel(INFO)
getLogger("ep_type").setLevel(INFO)


NUM_RANDOM_GRAPHS = 1000
FILENAME = join(dirname(__file__), "data/random_internal_graph.json")
if not exists(FILENAME):
    with open(FILENAME, "w", encoding="utf-8") as f:
        dump([random_internal_graph(liv, True, 1).json_obj() for _ in trange(NUM_RANDOM_GRAPHS)], f, indent=4, sort_keys=True)

with open(FILENAME, "r", encoding="utf-8") as f:
    RANDOM_GRAPHS: list[internal_graph] = [internal_graph({ep.key(): ep for ep in json_igraph}) for json_igraph in load(f)]
