"""OntologyFunction — server-side business logic on ontology objects."""

from dataclasses import dataclass
from typing import Any, Callable

from foundry_ontology.core.data_types import PropertyType


@dataclass
class OntologyFunction:
    """Server-side business logic — equivalent to Foundry's @Function() decorator."""

    function_id: str
    display_name: str
    description: str = ""
    input_types: dict[str, PropertyType] = None
    output_type: str = ""  # ObjectType ID or PropertyType
    implementation: Callable[..., Any] = None

    def __post_init__(self):
        if self.input_types is None:
            self.input_types = {}

    def execute(self, **kwargs: Any) -> Any:
        """Execute the function with given arguments."""
        if self.implementation is None:
            raise RuntimeError(f"Function {self.function_id} has no implementation")
        return self.implementation(**kwargs)

    def describe(self) -> dict:
        """JSON-serializable for MCP tool listing."""
        return {
            "function_id": self.function_id,
            "display_name": self.display_name,
            "description": self.description,
            "inputs": {k: v.value for k, v in self.input_types.items()},
            "output_type": self.output_type,
        }
