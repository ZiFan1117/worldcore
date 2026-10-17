"""Ontology — master registry of all types."""

from dataclasses import dataclass, field
from typing import Optional

from foundry_ontology.core.action_type import ActionType
from foundry_ontology.core.function import OntologyFunction
from foundry_ontology.core.interface import Interface
from foundry_ontology.core.link_type import LinkType
from foundry_ontology.core.object_type import ObjectType


@dataclass
class Ontology:
    """Master registry — equivalent to a Foundry Ontology."""

    ontology_id: str
    display_name: str
    version: str = "1.0.0"
    description: str = ""
    object_types: dict[str, ObjectType] = field(default_factory=dict)
    link_types: dict[str, LinkType] = field(default_factory=dict)
    action_types: dict[str, ActionType] = field(default_factory=dict)
    functions: dict[str, OntologyFunction] = field(default_factory=dict)
    interfaces: dict[str, Interface] = field(default_factory=dict)

    def register_object_type(self, ot: ObjectType) -> None:
        self.object_types[ot.type_id] = ot

    def register_link_type(self, lt: LinkType) -> None:
        self.link_types[lt.link_id] = lt

    def register_action_type(self, at: ActionType) -> None:
        self.action_types[at.action_id] = at

    def register_function(self, fn: OntologyFunction) -> None:
        self.functions[fn.function_id] = fn

    def register_interface(self, iface: Interface) -> None:
        self.interfaces[iface.interface_id] = iface

    def get_linked_types(self, type_id: str) -> list[LinkType]:
        """Get all LinkTypes where the given type is source or target."""
        return [
            lt
            for lt in self.link_types.values()
            if lt.source_type == type_id or lt.target_type == type_id
        ]

    def validate_ontology(self) -> list[str]:
        """Check referential integrity. Returns list of error messages."""
        errors: list[str] = []
        for lt in self.link_types.values():
            if lt.source_type not in self.object_types:
                errors.append(f"Link {lt.link_id}: source_type '{lt.source_type}' not found")
            if lt.target_type not in self.object_types:
                errors.append(f"Link {lt.link_id}: target_type '{lt.target_type}' not found")
        for ot in self.object_types.values():
            for iface_id in ot.interfaces:
                if iface_id not in self.interfaces:
                    errors.append(f"ObjectType {ot.type_id}: interface '{iface_id}' not found")
        return errors

    def summary(self) -> dict:
        """Counts of each type."""
        return {
            "object_types": len(self.object_types),
            "link_types": len(self.link_types),
            "action_types": len(self.action_types),
            "functions": len(self.functions),
            "interfaces": len(self.interfaces),
        }

    def to_dict(self) -> dict:
        """Full JSON export of ontology."""
        return {
            "ontology_id": self.ontology_id,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "object_types": {k: _object_type_to_dict(v) for k, v in self.object_types.items()},
            "link_types": {
                k: {
                    "link_id": v.link_id,
                    "display_name": v.display_name,
                    "source_type": v.source_type,
                    "target_type": v.target_type,
                    "cardinality": v.cardinality.value,
                }
                for k, v in self.link_types.items()
            },
            "action_types": {k: v.describe() for k, v in self.action_types.items()},
            "functions": {k: v.describe() for k, v in self.functions.items()},
            "interfaces": {
                k: {
                    "interface_id": v.interface_id,
                    "display_name": v.display_name,
                    "required_properties": [p.name for p in v.required_properties],
                }
                for k, v in self.interfaces.items()
            },
        }


def _object_type_to_dict(ot: ObjectType) -> dict:
    return {
        "type_id": ot.type_id,
        "display_name": ot.display_name,
        "description": ot.description,
        "primary_key": ot.primary_key,
        "properties": list(ot.properties.keys()),
        "interfaces": ot.interfaces,
    }
