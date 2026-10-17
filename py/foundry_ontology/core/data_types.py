"""Property types and value types mirroring Foundry's data type system.

Value types are semantic wrappers around a field type comprised of metadata
and constraints — equivalent to Foundry's approach.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PropertyType(Enum):
    """Base field types that mirror Foundry's data types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    GEOHASH = "geohash"
    GEOSHAPE = "geoshape"
    ATTACHMENT = "attachment"
    MARKING = "marking"
    OBJECT_REFERENCE = "object_reference"


@dataclass
class ValueType:
    """Semantic wrapper around PropertyType with metadata and constraints.

    Equivalent to Foundry's "Value types are semantic wrappers around a field
    type comprised of metadata and constraints."
    """

    name: str
    base_type: PropertyType
    constraints: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a value against this type's constraints.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if value is None:
            return True, None

        # Type check
        try:
            self._check_base_type(value)
        except (TypeError, ValueError) as e:
            return False, str(e)

        # Constraint checks
        if "pattern" in self.constraints:
            import re

            pattern = self.constraints["pattern"]
            if not re.match(pattern, str(value)):
                return False, f"Value does not match pattern {pattern}"

        if "min" in self.constraints:
            try:
                if float(value) < self.constraints["min"]:
                    return False, f"Value must be >= {self.constraints['min']}"
            except (TypeError, ValueError):
                return False, "Value must be numeric for min constraint"

        if "max" in self.constraints:
            try:
                if float(value) > self.constraints["max"]:
                    return False, f"Value must be <= {self.constraints['max']}"
            except (TypeError, ValueError):
                return False, "Value must be numeric for max constraint"

        if "minLength" in self.constraints:
            if len(str(value)) < self.constraints["minLength"]:
                return False, f"Value must have length >= {self.constraints['minLength']}"

        if "maxLength" in self.constraints:
            if len(str(value)) > self.constraints["maxLength"]:
                return False, f"Value must have length <= {self.constraints['maxLength']}"

        if "in" in self.constraints:
            if value not in self.constraints["in"]:
                return False, f"Value must be one of {self.constraints['in']}"

        return True, None

    def _check_base_type(self, value: Any) -> None:
        """Check that value matches the base PropertyType."""
        if self.base_type == PropertyType.STRING and not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value).__name__}")
        if self.base_type == PropertyType.INTEGER:
            if isinstance(value, bool):
                raise TypeError("Expected int, got bool")
            if not isinstance(value, int):
                try:
                    int(value)
                except (TypeError, ValueError):
                    raise TypeError(f"Expected int, got {type(value).__name__}")
        if self.base_type in (PropertyType.FLOAT, PropertyType.DECIMAL) and not isinstance(
            value, (int, float)
        ):
            try:
                float(value)
            except (TypeError, ValueError):
                raise TypeError(f"Expected float/decimal, got {type(value).__name__}")
        if self.base_type == PropertyType.BOOLEAN and not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {type(value).__name__}")
        if self.base_type == PropertyType.DATE:
            if not hasattr(value, "year"):
                raise TypeError("Expected date-like object")
        if self.base_type == PropertyType.DATETIME or self.base_type == PropertyType.TIMESTAMP:
            if not hasattr(value, "year") or not hasattr(value, "hour"):
                raise TypeError("Expected datetime-like object")
        if self.base_type == PropertyType.OBJECT_REFERENCE and not isinstance(value, str):
            raise TypeError(f"Expected str (instance_id), got {type(value).__name__}")
