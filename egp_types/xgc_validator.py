"""Validate & normalise JSON Genetic Code definitions."""

from copy import deepcopy
from datetime import datetime
from json import load
from os.path import dirname, join
from typing import Any, cast

from egp_utils.base_validator import base_validator
from egp_utils.common import merge

from .conversions import encode_properties, decode_properties
from .ep_type import validate
from .gc_graph import gc_graph
from .gc_type_tools import PROPERTIES, define_signature, PHYSICAL_PROPERTY


# Storage types schemas
# NOTE: Cerberus can modfiy a schmea (specifically I noticed "oneof_schema" --> "one_of") so
# we deepcopy the schema before creating the validator to ensure it is not modified for other use.

# The Genetic Material Store (GMS) is the abstract common base schema for LGC & GGC
with open(join(dirname(__file__), "formats/gms_entry_format.json"), "r", encoding="utf8") as file_ptr:
    GMS_ENTRY_SCHEMA: dict[str, dict[str, Any]] = load(file_ptr)
_GMS_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(GMS_ENTRY_SCHEMA)

# LGC is the storage schema for the Genomic Libray
LGC_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(GMS_ENTRY_SCHEMA)
with open(join(dirname(__file__), "formats/LGC_entry_format.json"), "r", encoding="utf8") as file_ptr:
    merge(LGC_ENTRY_SCHEMA, load(file_ptr), update=True)
_LGC_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(LGC_ENTRY_SCHEMA)

LGC_JSON_LOAD_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(LGC_ENTRY_SCHEMA)
with open(
    join(dirname(__file__), "formats/LGC_json_load_entry_format.json"),
    "r",
    encoding="utf8",
) as file_ptr:
    merge(LGC_JSON_LOAD_ENTRY_SCHEMA, load(file_ptr), update=True)
_LGC_JSON_LOAD_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(LGC_JSON_LOAD_ENTRY_SCHEMA)

LGC_JSON_DUMP_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(LGC_ENTRY_SCHEMA)
with open(
    join(dirname(__file__), "formats/LGC_json_dump_entry_format.json"),
    "r",
    encoding="utf8",
) as file_ptr:
    merge(LGC_JSON_DUMP_ENTRY_SCHEMA, load(file_ptr), update=True)
_LGC_JSON_DUMP_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(LGC_JSON_DUMP_ENTRY_SCHEMA)

# GGC is the storage schema for the Gene Pool
GGC_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(GMS_ENTRY_SCHEMA)
with open(join(dirname(__file__), "formats/gGC_entry_format.json"), "r", encoding="utf8") as file_ptr:
    merge(GGC_ENTRY_SCHEMA, load(file_ptr), update=True)
_GGC_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(GGC_ENTRY_SCHEMA)

# XGC_ENTRY_SCHEMA is the superset schema from which transient xGC's can be validated
XGC_ENTRY_SCHEMA: dict[str, dict[str, Any]] = deepcopy(GGC_ENTRY_SCHEMA)
merge(XGC_ENTRY_SCHEMA, LGC_ENTRY_SCHEMA, update=True)


class _gms_entry_validator(base_validator):
    # TODO: Make errors ValidationError types for full disclosure
    # https://docs.python-cerberus.org/en/stable/customize.html#validator-error

    def _check_with_valid__e_count(self, field: str, value: int) -> None:
        if not value and self.document["_evolvability"] > 0.0:
            self._error(field, "_e_count cannot be 0 if _evolvability is non-zero.")
        if value > self.document["e_count"]:
            self._error(
                field,
                f"_e_count ({value}) cannot be greater than e_count ({self.document['e_count']})",
            )

    def _check_with_valid__evolvability(self, field: str, value: float) -> None:
        if value > 0.0 and not self.document["_e_count"]:
            self._error(field, "_e_count cannot be 0 if _evolvability is non-zero.")

    def _valid_pgc(self, field: str, value: Any) -> bool:
        pgc_none: dict[str, bool] = {k: v is None for k, v in self.document.items() if "pgc_" in k and "pgc_ref" not in k}
        if (value is None and not all(pgc_none.values())) or (value is not None and any(pgc_none.values())):
            pgc_defined: list[str] = [k for k, v in pgc_none.items() if not v]
            pgc_undefined: list[str] = [k for k, v in pgc_none.items() if v]
            self._error(
                field,
                f"pGC fields only partially defined. Defined: {pgc_defined}, Undefined: {pgc_undefined}.",
            )
            return False
        return value is not None

    def _check_with_valid__pgc_e_count(self, field: str, value: Any) -> None:
        if self._valid_pgc(field, value):
            evolve: list[float] | tuple[float, ...] = self.document["_pgc_evolvability"]
            invalid: dict[int, bool] = {i: v == 0 and evolve[i] > 0.0 for i, v in enumerate(value)}
            if any(invalid.values()):
                indices: list[int] = [i for i, v in invalid.items() if not v]
                self._error(
                    field,
                    f"_pgc_e_count cannot be 0 if _pgc_evolvability is non-zero at indices {indices}.",
                )
            e_count: list[float] | tuple[float, ...] = self.document["pgc_e_count"]
            invalid: dict[int, bool] = {i: e_count[i] > v for i, v in enumerate(value)}
            if any(invalid.values()):
                indices: list[int] = [i for i, v in invalid.items() if not v]
                self._error(field, f"_pgc_e_count cannot be > pgc_e_count at indices {indices}.")

    def _check_with_valid__pgc_evolvability(self, field: str, value: Any) -> None:
        self._valid_pgc(field, value)

    def _check_with_valid__pgc_f_count(self, field: str, value: Any) -> None:
        if self._valid_pgc(field, value):
            invalid: dict[int, bool] = {i: v == 0 and self.document["_pgc_fitness"][i] > 0.0 for i, v in enumerate(value)}
            if any(invalid.values()):
                indices: list[int] = [i for i, v in invalid.items() if not v]
                self._error(
                    field,
                    f"_pgc_f_count cannot be 0 if _pgc_fitness is non-zero at indices {indices}.",
                )
            f_count: list[float] | tuple[float, ...] = self.document["pgc_f_count"]
            invalid: dict[int, bool] = {i: f_count[i] > v for i, v in enumerate(value)}
            if any(invalid.values()):
                indices: list[int] = [i for i, v in invalid.items() if not v]
                self._error(field, f"_pgc_f_count cannot be > pgc_f_count at indices {indices}.")

    def _check_with_valid__pgc_fitness(self, field: str, value: Any) -> None:
        self._valid_pgc(field, value)

    def _check_with_valid__reference_count(self, field: str, value: Any) -> None:
        if value > self.document["reference_count"]:
            self._error(
                field,
                f"_reference_count ({value}) cannot be > reference_count {self.document['reference_count']}.",
            )

    def _check_with_valid_created(self, field: str, value: datetime) -> None:
        if value > datetime.utcnow():
            self._error(
                field,
                "Created date-time cannot be in the future. Is the system clock correct?",
            )
        if self.document.get("updated") is not None:
            if self.document["updated"] < value:
                self._error(field, "A record cannot be updated before it has been created.")

    def _check_with_valid_e_count(self, field: str, value: Any) -> None:
        if value == 1 and self.document["evolvability"] < 1.0:
            self._error(field, "e_count cannot be 1 if evolvability has changed (is not 1.0).")
        if value < self.document["_e_count"]:
            self._error(
                field,
                f"e_count ({value}) cannot be less than _e_count ({self.document['_e_count']})",
            )

    def _check_with_valid_evolvability(self, field: str, value: Any) -> None:
        if value < 1.0 and self.document["e_count"] == 1:
            self._error(field, "e_count cannot be 1 if evolvability has changed (is not 1.0).")

    def _check_with_valid_graph(self, field: str, value: Any) -> None:
        graph: gc_graph = gc_graph(value)
        if not graph.validate():
            self._error(field, f"graph is invalid: {graph.status}")

    def _check_with_valid_ep_type(self, field: str, value: Any) -> None:
        if not validate(value):
            self._error(field, f"ep_type {value} does not exist.")

    def _check_with_valid_input_types(self, field: str, value: Any) -> None:
        all_types: set[int] = set(range(len(value)))
        all_refs: set[int] = set((idx for idx in self.document["inputs"]))
        if all_types != all_refs:
            self._error(
                field,
                f"Input types at indices {all_types - all_refs} are not referenced by inputs.",
            )

    def _check_with_valid_inputs(self, field: str, value: Any) -> None:
        num_types: int = len(self.document["input_types"])
        invalid_indices: list[int] = [idx for idx in value if idx > num_types]
        if invalid_indices:
            self._error(field, f"Invalid inputs indices: {invalid_indices}")

    def _check_with_valid_num_inputs(self, field: str, value: Any) -> None:
        if value != len(self.document["inputs"]):
            self._error(
                field,
                f"num_inputs ({value}) != length of inputs ({len(self.document['inputs'])}).",
            )

    def _check_with_valid_num_outputs(self, field: str, value: Any) -> None:
        if value != len(self.document["outputs"]):
            self._error(
                field,
                f"num_outputs ({value}) != length of outputs ({len(self.document['outputs'])}.",
            )

    def _check_with_valid_output_types(self, field: str, value: Any) -> None:
        all_types: set[int] = set(range(len(value)))
        all_refs: set[int] = set((idx for idx in self.document["outputs"]))
        if all_types != all_refs:
            self._error(
                field,
                f"Output types at indices {all_types - all_refs} are not referenced by outputs.",
            )

    def _check_with_valid_outputs(self, field: str, value: Any) -> None:
        num_types: int = len(self.document["output_types"])
        invalid_indices: list[int] = [idx for idx in value if idx > num_types]
        if invalid_indices:
            self._error(field, f"Invalid outputs indices: {invalid_indices}")

    def _check_with_valid_pgc_e_count(self, field: str, value: Any) -> None:
        if self._valid_pgc(field, value):
            invalid: dict[int, bool] = {i: v == 1 and self.document["pgc_evolvability"][i] < 1.0 for i, v in enumerate(value)}
            if any(invalid.values()):
                indices: list[int] = [i for i, v in invalid.items() if not v]
                self._error(
                    field,
                    f"pgc_e_count cannot be 1 if pgc_evolvability has changed (is not 1.0) at indices {indices}.",
                )

            _invalid: list[int] = [idx for idx, pgc_e_count in enumerate(value) if pgc_e_count < self.document["_pgc_e_count"][idx]]
            if _invalid:
                self._error(
                    field,
                    f"_pgc_e_count is greater than pgc_e_count at indices: {_invalid}",
                )

    def _check_with_valid_pgc_f_count(self, field: str, value: Any) -> None:
        if self._valid_pgc(field, value):
            invalid: dict[int, bool] = {i: v == 1 and self.document["pgc_fitness"][i] < 1.0 for i, v in enumerate(value)}
            if any(invalid.values()):
                indices: list[int] = [i for i, v in invalid.items() if not v]
                self._error(
                    field,
                    f"pgc_f_count {list(invalid.values())} cannot be 1 if pgc_fitness has changed (is not 1.0) at indices {indices}.",
                )

            _invalid: list[int] = [idx for idx, pgc_f_count in enumerate(value) if pgc_f_count < self.document["_pgc_f_count"][idx]]
            if _invalid:
                self._error(
                    field,
                    f"_pgc_f_count is greater than pgc_f_count at indices: {_invalid}",
                )

    def _check_with_valid_pgc_fitness(self, field: str, value: Any) -> None:
        if self._valid_pgc(field, value):
            # FIXME: Can do more here to determine a valid pGC
            if not any(t < 0 for t in self.document.get("input_types", [0])):
                self._error(field, "A pGC must have at least 1 xGC type input.")
            if not any(t < 0 for t in self.document.get("output_types", [0])):
                self._error(field, "A pGC must have at least 1 xGC type output.")
            if not PHYSICAL_PROPERTY & self.document["properties"]:
                self._error(field, "A pGC must have the physical property set.")
        else:
            # If there are no errors then it must be a gGC
            # FIXME: Can do more here to determine a valid gGC
            if value is not None:
                self._error(field, "A gGC must NOT have pgc_fitness.")

    def _check_with_valid_properties(self, field: str, value: Any) -> None:
        valid_property_mask: int = 0
        for valid_property in PROPERTIES.values():
            valid_property_mask |= valid_property
        invalid_properties: int = (valid_property_mask & value) ^ value
        if invalid_properties:
            self._error(
                field,
                f"Invalid properties set in the positions: {hex(invalid_properties)}.",
            )

    def _check_with_valid_reference_count(self, field: str, value: Any) -> None:
        if value < self.document["_reference_count"]:
            self._error(
                field,
                f"reference_count ({value}) cannot be lower than _reference_count {self.document['_reference_count']}.",
            )

    def _check_with_valid_updated(self, field: str, value: datetime) -> None:
        if value > datetime.utcnow():
            self._error(
                field,
                "Updated date-time cannot be in the future. Is the system clock correct?",
            )
        if self.document.get("created") is not None:
            if self.document["updated"] > value:
                self._error(field, "A record cannot be updated before it has been created.")

    def _normalize_default_setter_set_input_types(self, document) -> list[int]:
        # Gather all the input endpoint types. Reduce in a set then order the list.
        inputs: list[int] = []
        for row in document["graph"].values():
            inputs.extend([ep[2] for ep in filter(lambda x: x[0] == "I", row)])
        return sorted(set(inputs))

    def _normalize_default_setter_set_output_types(self, document) -> list[int]:
        # Gather all the output endpoint types. Reduce in a set then order the list.
        return sorted(set([ep[2] for ep in document["graph"].get("O", tuple())]))

    def _normalize_default_setter_set_input_indices(self, document) -> bytes:
        # Get the type list then find all the inputs in order & look them up.
        type_list: list[int] = self._normalize_default_setter_set_input_types(document)
        inputs: set[tuple[str | int, ...]] = {tuple(ep) for row in document["graph"].values() for ep in filter(lambda x: x[0] == "I", row)}
        return bytes((type_list.index(cast(int, ep[2])) for ep in sorted(inputs, key=lambda x: x[1])))

    def _normalize_default_setter_set_output_indices(self, document) -> bytes:
        # Get the type list then find all the inputs in order & look them up.
        type_list: list[int] = self._normalize_default_setter_set_output_types(document)
        return bytes((type_list.index(ep[2]) for ep in sorted(document["graph"].get("O", tuple()), key=lambda x: x[1])))

    def _normalize_default_setter_set_num_inputs(self, document) -> int:
        inputs: set[int] = set()
        for row in document["graph"].values():
            for ep in filter(lambda x: x[0] == "I", row):
                inputs.add(ep[1])
        return len(inputs)

    def _normalize_default_setter_set_num_outputs(self, document) -> int:
        return len(document["graph"].get("O", tuple()))

    def _normalize_default_setter_set_updated(self, _) -> datetime:
        return datetime.utcnow()

    def _normalize_coerce_memoryview_to_bytes(self, value) -> bytes:
        return bytes(value)


class _LGC_entry_validator(_gms_entry_validator):
    # TODO: Make errors ValidationError types for full disclosure
    # https://docs.python-cerberus.org/en/stable/customize.html#validator-error

    def _check_with_valid_ancestor_a(self, field: str, value: Any) -> None:
        if value is None and self.document["generation"]:
            self._error(
                field,
                "GC has no primary parent (ancestor A) but is not a codon (0th generation).",
            )
        if value is not None and not self.document["generation"]:
            self._error(
                field,
                "GC has a primary parent (ancestor A) but is a codon (0th generation).",
            )
        if value is not None and value == self.document["signature"]:
            self._error(field, "A GC cannot be its own ancestor (A).")

    def _check_with_valid_ancestor_b(self, field: str, value: Any) -> None:
        if value is not None and self.document["ancestor_a"] is None:
            self._error(
                field,
                "GC has a secondary parent (ancestor B) but no primary parent (ancestor A).",
            )
        if value is not None and value == self.document["signature"]:
            self._error(field, "A GC cannot be its own ancestor (B).")

    def _check_with_valid_missing_links_a(self, field: str, value: Any) -> None:
        if value == 0 and not self.document["closest_surviving_ancestor_a"] is None:
            self._error(
                field,
                "Closest surviving ancestor A is set but there are no missing links.",
            )
        if value > 0 and self.document["closest_surviving_ancestor_a"] is None:
            self._error(
                field,
                "Closest surviving ancestor A is not set but there are missing links.",
            )

    def _check_with_valid_missing_links_b(self, field: str, value: Any) -> None:
        if value == 0 and not self.document["closest_surviving_ancestor_b"] is None:
            self._error(
                field,
                "Closest surviving ancestor B is set but there are no missing links.",
            )
        if value > 0 and self.document["closest_surviving_ancestor_b"] is None:
            self._error(
                field,
                "Closest surviving ancestor B is not set but there are missing links.",
            )

    def _check_with_valid_lost_descendants(self, field: str, value: Any) -> None:
        if value > 0 and self.document["e_count"] == 1:
            self._error(field, "GC has not evolved but has lost descendants")

    def _check_with_valid_gca(self, field: str, value: Any) -> None:
        if "A" in self.document["graph"] and value is None:
            self._error(field, "graph references row A but gca is None.")
        if "A" not in self.document["graph"] and value is not None:
            self._error(field, "No reference to row A in graph but gca is not None.")
        if value is not None and value == self.document["signature"]:
            self._error(field, "A GC cannot reference itself in row A.")

    def _check_with_valid_gcb(self, field: str, value: Any) -> None:
        if "B" in self.document["graph"] and value is None:
            self._error(field, "graph references row B but gcb is None.")
        if value is not None and self.document["gca"] is None:
            self._error(field, "gcb is defined but gca is None.")
        if value is not None and value == self.document["signature"]:
            self._error(field, "A GC cannot reference itself in row B.")

    def _check_with_valid_pgc(self, field: str, value: Any) -> None:
        if self.document["generation"] and value is None:
            self._error(field, "Generation is > 0 but pgc is None.")
        if not self.document["generation"] and value is not None:
            self._error(field, f"Generation is 0 but pgc is defined as {value}.")
        if self.document["ancestor_a"] is None and value is not None:
            self._error(
                field,
                f"GC has no primary parent (ancestor A) but pgc is defined as {value}.",
            )
        if value is not None and value == self.document["signature"]:
            self._error(field, "A GC cannot have been created by itself (pgc == signature).")

    def _normalize_default_setter_set_signature(self, _) -> bytes:
        return define_signature(self.document)


class _LGC_json_load_entry_validator(_LGC_entry_validator):
    # TODO: Make errors ValidationError types for full disclosure
    # https://docs.python-cerberus.org/en/stable/customize.html#validator-error

    def _normalize_coerce_properties_dict_to_int(self, value) -> int:
        return encode_properties(value)

    def _normalize_coerce_type_indices_str_to_binary(self, value: str | bytes) -> bytes:
        return bytes.fromhex(value) if isinstance(value, str) else value


class _LGC_json_dump_entry_validator(_LGC_entry_validator):
    # TODO: Make errors ValidationError types for full disclosure
    # https://docs.python-cerberus.org/en/stable/customize.html#validator-error

    def _normalize_coerce_properties_int_to_dict(self, value) -> dict[str, bool]:
        return decode_properties(value)

    def _normalize_coerce_type_indices_binary_to_str(self, value: str | bytes) -> str | None:
        return value.hex() if isinstance(value, (bytes, memoryview, bytearray)) else value


class _gGC_entry_validator(_gms_entry_validator):
    def _check_with_valid_ancestor_a_ref(self, field: str, value: Any) -> None:
        if value is None and self.document["generation"]:
            self._error(
                field,
                "GC has no primary parent (ancestor A) but is not a codon (0th generation).",
            )
        if value is not None and not self.document["generation"]:
            self._error(
                field,
                "GC has a primary parent (ancestor A) but is a codon (0th generation).",
            )
        if value is not None and value == self.document["ref"]:
            self._error(field, "A GC cannot be its own ancestor (A).")

    def _check_with_valid_ancestor_b_ref(self, field: str, value: Any) -> None:
        if value is not None and self.document["ancestor_a_ref"] is None:
            self._error(
                field,
                "GC has a secondary parent (ancestor B) but no primary parent (ancestor A).",
            )
        if value is not None and value == self.document["ref"]:
            self._error(field, "A GC cannot be its own ancestor (B).")

    def _check_with_valid_gca_ref(self, field: str, value: Any) -> None:
        if "A" in self.document["graph"] and value is None:
            self._error(field, "graph references row A but gca_ref is None.")
        if "A" not in self.document["graph"] and value is not None:
            self._error(field, "No reference to row A in graph but gca_ref is not None.")
        if value is not None and value == self.document["ref"]:
            self._error(field, "A GC cannot reference itself in row A.")

    def _check_with_valid_gcb_ref(self, field: str, value: Any) -> None:
        if "B" in self.document["graph"] and value is None:
            self._error(field, "graph references row B but gcb_ref is None.")
        if "B" not in self.document["graph"] and value is not None:
            self._error(field, "No reference to row B in graph but gcb_ref is not None.")
        if value is not None and self.document["gca"] is None:
            self._error(field, "gcb_ref is defined but gca_ref is None.")

    def _check_with_valid_pgc_ref(self, field: str, value: Any) -> None:
        if self.document["generation"] and value is None:
            self._error(field, "Generation is > 0 but pgc_ref is None.")
        if not self.document["generation"] and value is not None:
            self._error(field, f"Generation is 0 but pgc_ref is defined as {value}.")
        if self.document["ancestor_a"] is None and value is not None:
            self._error(
                field,
                f"GC has no primary parent (ancestor A) but pgc_ref is defined as {value}.",
            )
        if value is not None and value == self.document["ref"]:
            self._error(field, "A GC cannot have been created by itself (pgc_ref == ref).")


gms_entry_validator: _gms_entry_validator = _gms_entry_validator(_GMS_ENTRY_SCHEMA)
LGC_entry_validator: _LGC_entry_validator = _LGC_entry_validator(_LGC_ENTRY_SCHEMA)
LGC_json_load_entry_validator: _LGC_json_load_entry_validator = _LGC_json_load_entry_validator(_LGC_JSON_LOAD_ENTRY_SCHEMA)
LGC_json_dump_entry_validator: _LGC_json_dump_entry_validator = _LGC_json_dump_entry_validator(_LGC_JSON_DUMP_ENTRY_SCHEMA)
gGC_entry_validator: _gGC_entry_validator = _gGC_entry_validator(_GGC_ENTRY_SCHEMA, purge_unknown=True)


class xgc_validator_generator(_gGC_entry_validator, _LGC_entry_validator):
    """Superset validator from which to derive transient xGC type validators."""
