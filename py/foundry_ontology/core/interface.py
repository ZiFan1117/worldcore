"""Interface — polymorphic shape for ObjectTypes."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from foundry_ontology.core.object_type import ObjectType, Property

if TYPE_CHECKING:
    from foundry_ontology.core.ontology import Ontology


@dataclass
class Interface:
    """Shared shape that multiple ObjectTypes can implement."""

    interface_id: str
    display_name: str
    description: str = ""
    required_properties: list[Property] = None

    def __post_init__(self):
        if self.required_properties is None:
            self.required_properties = []

    def check_compliance(self, object_type: ObjectType) -> bool:
        """Check if an ObjectType has all required properties of this interface."""
        for req_prop in self.required_properties:
            obj_prop = object_type.get_property(req_prop.name)
            if obj_prop is None:
                return False
            if obj_prop.property_type != req_prop.property_type:
                return False
        return True

    def get_implementors(self, ontology: "Ontology") -> list[ObjectType]:
        """Get all ObjectTypes that implement this interface."""
        return [
            ot
            for ot in ontology.object_types.values()
            if self.interface_id in ot.interfaces and self.check_compliance(ot)
        ]
