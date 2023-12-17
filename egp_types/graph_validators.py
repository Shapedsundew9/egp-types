"""Graph validators"""
from copy import deepcopy
from json import load
from logging import getLogger, INFO
from os.path import dirname, join
from typing import Any

from egp_utils.base_validator import base_validator
from cerberus.schema import RulesSetRegistry

from .ep_type import validate, MIN_EP_TYPE_VALUE, MAX_EP_TYPE_VALUE, ep_type_lookup


# Suppress noisy loggers
getLogger("eGC").setLevel(INFO)
getLogger("ep_type").setLevel(INFO)


# End point type values are used in may places. Making a rule set
# helps keep things consistent.
GRAPH_REGISTRY: RulesSetRegistry = RulesSetRegistry()
GRAPH_RULES_SET: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "ep_type",
        {
            "type": "integer",
            "min": MIN_EP_TYPE_VALUE,
            "max": MAX_EP_TYPE_VALUE,
            "check_with": "valid_ep_type",
        },
    ),
    (
        "ep_type_not_bool",
        {
            "type": "integer",
            "min": MIN_EP_TYPE_VALUE,
            "max": MAX_EP_TYPE_VALUE,
            "noneof": [
                {
                    "type": "integer",
                    "allowed": [ep_type_lookup["n2v"]["bool"]],
                }
            ],
            "check_with": "valid_ep_type",
        },
    ),
    (
        "ep_type_only_bool",
        {"type": "integer", "min": ep_type_lookup["n2v"]["bool"], "max": ep_type_lookup["n2v"]["bool"]},
    ),
    (
        "ep_idx",
        {
            "type": "integer",
            "min": 0,
            "max": 255,
        },
    ),
    (
        # This can by any valid python constant or object instanciation expression
        "ep_const_value",
        {"minlength": 1, "maxlength": 128, "type": "string"},
    ),
)
GRAPH_REGISTRY.extend(deepcopy(GRAPH_RULES_SET))


# The Genetic Material Store (GMS) is the abstract common base schema for LGC & GGC
with open(join(dirname(__file__), "formats/gms_entry_format.json"), "r", encoding="utf8") as file_ptr:
    GRAPH_SCHEMA: dict[str, dict[str, Any]] = {"graph": load(file_ptr)["graph"]}
del GRAPH_SCHEMA["graph"]["check_with"]
_GRAPH_SCHEMA: dict[str, dict[str, Any]] = deepcopy(GRAPH_SCHEMA)

# Internal Graph Schema
with open(
    join(dirname(__file__), "formats/internal_graph_format.json"),
    "r",
    encoding="utf8",
) as file_ptr:
    INTERNAL_GRAPH_SCHEMA: dict[str, dict[str, Any]] = load(file_ptr)
_INTERNAL_GRAPH_SCHEMA: dict[str, dict[str, Any]] = deepcopy(INTERNAL_GRAPH_SCHEMA)

# Create a limited version that does not have such long lists for random generation
LIMITED_INTERNAL_GRAPH_SCHEMA: dict[str, dict[str, Any]] = deepcopy(INTERNAL_GRAPH_SCHEMA)
LIMITED_INTERNAL_GRAPH_SCHEMA["internal_graph"]["maxlength"] = 64
for ep in LIMITED_INTERNAL_GRAPH_SCHEMA["internal_graph"]["valuesrules"]["oneof"]:
    if "anyof" in ep["valuesrules"]:
        for epdef in ep["valuesrules"]["anyof"]:
            epdef["items"][4]["maxlength"] = 8
    else:
        ep["valuesrules"]["items"][4]["maxlength"] = 8
_LIMITED_INTERNAL_GRAPH_SCHEMA: dict[str, dict[str, Any]] = deepcopy(LIMITED_INTERNAL_GRAPH_SCHEMA)


class base_graph_validator(base_validator):
    # TODO: Make errors ValidationError types for full disclosure
    # https://docs.python-cerberus.org/en/stable/customize.html#validator-error

    def _check_with_valid_ep_type(self, field: str, value: Any) -> None:
        if not validate(value):
            self._error(field, f"ep_type {value} does not exist.")


graph_validator: base_graph_validator = base_graph_validator()
igraph_validator: base_graph_validator = base_graph_validator()
limited_igraph_validator: base_graph_validator = base_graph_validator()
graph_validator.rules_set_registry = GRAPH_REGISTRY
igraph_validator.rules_set_registry = GRAPH_REGISTRY
limited_igraph_validator.rules_set_registry = GRAPH_REGISTRY
graph_validator.schema = _GRAPH_SCHEMA
igraph_validator.schema = _INTERNAL_GRAPH_SCHEMA
limited_igraph_validator.schema = _LIMITED_INTERNAL_GRAPH_SCHEMA
