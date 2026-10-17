"""ActionType definitions — the kinetic layer."""

from dataclasses import dataclass, field
from typing import Any, Optional

from foundry_ontology.core.data_types import PropertyType


@dataclass
class ActionParameter:
    """Parameter for an ActionType."""

    name: str
    param_type: PropertyType
    required: bool = True
    description: str = ""
    options: Optional[list[Any]] = None
    default: Optional[Any] = None


@dataclass
class ValidationRule:
    """Validation rule evaluated at action execution time."""

    rule_id: str
    expression: str
    message: str
    severity: str = "ERROR"


@dataclass
class ActionEffect:
    """What happens when the action executes successfully."""

    effect_type: str  # edit_object, create_object, create_link, delete_link, delete_object, notification
    target: str
    changes: dict = field(default_factory=dict)


@dataclass
class ActionType:
    """An action that can be executed with validation and effects."""

    action_id: str
    display_name: str = ""
    description: str = ""
    parameters: list[ActionParameter] = field(default_factory=list)
    validation_rules: list[ValidationRule] = field(default_factory=list)
    effects: list[ActionEffect] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    audit_enabled: bool = True
    # ★ 本格是【我们加的】（MIT 允许改）：AIOS 的动作元数据。
    #   放 not_roles（禁令）／kind（invoke 等）／implemented（有没有实现）等。
    #   为什么加：P 原本的 ActionType 没有 metadata 格，而这些信息挂在动作上。
    metadata: dict = field(default_factory=dict)

    def validate(self, context: dict[str, Any]) -> "ValidationResult":
        """Validate parameters and rules against execution context."""
        from foundry_ontology.core.object_type import ValidationResult

        errors: list[str] = []

        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in context:
                errors.append(f"Missing required parameter: {param.name}")
            elif param.name in context:
                val = context[param.name]
                if param.options and val not in param.options:
                    errors.append(f"Parameter '{param.name}' must be one of {param.options}")

        # Evaluate validation rules (expression has access to context)
        for rule in self.validation_rules:
            if rule.severity != "ERROR":
                continue
            try:
                # expression can use context keys as variables
                result = eval(rule.expression, {"__builtins__": {}}, context)
                if not result:
                    errors.append(rule.message)
            except Exception as e:
                errors.append(f"Validation error: {rule.message} ({e})")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    def describe(self) -> dict:
        """JSON-serializable description for agents."""
        return {
            "action_id": self.action_id,
            "display_name": self.display_name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type.value,
                    "required": p.required,
                    "options": p.options,
                }
                for p in self.parameters
            ],
            "required_roles": self.required_roles,
        }
