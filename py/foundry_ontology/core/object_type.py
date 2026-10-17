"""ObjectType and Property definitions — the semantic layer schema.

ObjectType is a SCHEMA DEFINITION (like a table DDL).
Object instances are stored separately in the ObjectStore.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from foundry_ontology.core.data_types import PropertyType, ValueType


@dataclass
class ValidationResult:
    """Result of validating instance data against an ObjectType."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(valid=True)

    @classmethod
    def failure(cls, errors: list[str]) -> "ValidationResult":
        return cls(valid=False, errors=errors)


@dataclass
class Property:
    """A property (field) on an ObjectType."""

    name: str
    display_name: str
    property_type: PropertyType
    value_type: Optional[ValueType] = None
    required: bool = False
    description: str = ""
    is_primary_key: bool = False
    options: Optional[list[Any]] = None

    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a single value. Returns (is_valid, error_message)."""
        if value is None or (isinstance(value, str) and value == ""):
            if self.required:
                return False, f"Property '{self.name}' is required"
            return True, None

        if self.value_type:
            return self.value_type.validate(value)

        # Basic type check without ValueType
        try:
            self._check_raw_type(value)
        except (TypeError, ValueError) as e:
            return False, str(e)

        if self.options is not None and value not in self.options:
            return False, f"Value must be one of {self.options}"

        return True, None

    def _check_raw_type(self, value: Any) -> None:
        """Check value matches property_type when no ValueType."""
        if self.property_type == PropertyType.STRING and not isinstance(value, str):
            raise TypeError(f"Expected str for {self.name}")
        if self.property_type == PropertyType.INTEGER:
            if isinstance(value, bool):
                raise TypeError(f"Expected int for {self.name}")
            if not isinstance(value, int):
                int(value)  # may raise
        if self.property_type in (PropertyType.FLOAT, PropertyType.DECIMAL):
            if not isinstance(value, (int, float)):
                float(value)
        if self.property_type == PropertyType.BOOLEAN and not isinstance(value, bool):
            raise TypeError(f"Expected bool for {self.name}")
        if self.property_type == PropertyType.OBJECT_REFERENCE and not isinstance(value, str):
            raise TypeError(f"Expected str (instance_id) for {self.name}")


@dataclass
class SharedProperty(Property):
    """A property that can be reused across multiple ObjectTypes."""

    used_by: list[str] = field(default_factory=list)


@dataclass
class ObjectType:
    """Schema definition for an object type — equivalent to Foundry ObjectType."""

    type_id: str
    display_name: str
    description: str = ""
    properties: dict[str, Property] = field(default_factory=dict)
    primary_key: str = ""
    interfaces: list[str] = field(default_factory=list)
    datasource: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def add_property(self, prop: Property) -> None:
        """Add a property to this object type."""
        self.properties[prop.name] = prop
        if prop.is_primary_key:
            self.primary_key = prop.name

    def get_property(self, name: str) -> Optional[Property]:
        """Get a property by name."""
        return self.properties.get(name)

    def validate_instance(self, data: dict[str, Any]) -> ValidationResult:
        """Validate instance data against this object type schema."""
        errors: list[str] = []

        # Check required properties
        for name, prop in self.properties.items():
            if prop.required and (name not in data or data[name] is None):
                errors.append(f"Missing required property: {name}")

        # Check primary key
        if self.primary_key and self.primary_key not in data and self.get_property(self.primary_key):
            pk_prop = self.get_property(self.primary_key)
            if pk_prop and pk_prop.required:
                errors.append(f"Missing primary key: {self.primary_key}")

        # Validate each provided value
        for name, value in data.items():
            if name not in self.properties:
                errors.append(f"Unknown property: {name}")
                continue
            prop = self.properties[name]
            valid, err = prop.validate_value(value)
            if not valid and err:
                errors.append(f"{name}: {err}")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def implements(self, interface_id: str) -> bool:
        """Check if this object type implements the given interface."""
        return interface_id in self.interfaces
