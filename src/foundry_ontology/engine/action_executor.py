"""Executes ActionTypes with validation, effects, and audit — the kinetic layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from foundry_ontology.core import ActionType, Ontology
from foundry_ontology.engine.audit_log import AuditEntry, AuditLog
from foundry_ontology.engine.object_store import ObjectStore


@dataclass
class ActionResult:
    """Result of executing an action."""

    success: bool
    action_id: str
    effects_applied: list[dict] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    audit_entry_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class ActionExecutor:
    """Executes ActionTypes with full validation, effects, and audit."""

    def __init__(self, ontology: Ontology, store: ObjectStore, audit: AuditLog):
        self.ontology = ontology
        self.store = store
        self.audit = audit

    def execute(
        self,
        action_type_id: str,
        params: dict,
        executed_by: str,
        context_resolver: Optional[Callable[[str, dict], dict]] = None,
        executed_by_roles: Optional[list[str]] = None,
    ) -> ActionResult:
        """Execute an action with validation, effects, and audit."""
        at = self.ontology.action_types.get(action_type_id)
        if not at:
            return ActionResult(
                success=False,
                action_id=action_type_id,
                validation_errors=[f"Unknown action type: {action_type_id}"],
            )

        # Role check (if roles provided and action requires them)
        if executed_by_roles is not None and at.required_roles:
            if not any(r in executed_by_roles for r in at.required_roles):
                return ActionResult(
                    success=False,
                    action_id=action_type_id,
                    validation_errors=["Insufficient role to execute this action"],
                )

        # Build context for validation (params + any resolved objects)
        context = dict(params)
        if context_resolver:
            resolved = context_resolver(action_type_id, params)
            if resolved:
                context.update(resolved)

        # Validate
        result = at.validate(context)
        if not result.valid:
            entry = AuditEntry(
                entry_id="",
                timestamp=datetime.now(),
                action_type_id=action_type_id,
                executed_by=executed_by,
                parameters=params,
                effects=[],
                success=False,
                error_message="; ".join(result.errors),
            )
            eid = self.audit.append(entry)
            return ActionResult(
                success=False,
                action_id=action_type_id,
                validation_errors=result.errors,
                audit_entry_id=eid,
            )

        # Apply effects
        effects_applied: list[dict] = []
        for effect in at.effects:
            try:
                self._apply_effect(effect, params, effects_applied)
            except Exception as e:
                entry = AuditEntry(
                    entry_id="",
                    timestamp=datetime.now(),
                    action_type_id=action_type_id,
                    executed_by=executed_by,
                    parameters=params,
                    effects=effects_applied,
                    success=False,
                    error_message=str(e),
                )
                self.audit.append(entry)
                return ActionResult(
                    success=False,
                    action_id=action_type_id,
                    effects_applied=effects_applied,
                    validation_errors=[str(e)],
                )

        # Audit
        entry = AuditEntry(
            entry_id="",
            timestamp=datetime.now(),
            action_type_id=action_type_id,
            executed_by=executed_by,
            parameters=params,
            effects=effects_applied,
            success=True,
        )
        eid = self.audit.append(entry)

        return ActionResult(
            success=True,
            action_id=action_type_id,
            effects_applied=effects_applied,
            audit_entry_id=eid,
        )

    def _apply_effect(self, effect: Any, params: dict, effects_applied: list[dict]) -> None:
        """Apply a single action effect."""
        if effect.effect_type == "edit_object":
            target_id = (
                effect.changes.get("instance_id")
                or params.get("instance_id")
                or params.get("asset_id")
                or params.get("target_id")
            )
            if target_id:
                self.store.update(target_id, effect.changes)
                effects_applied.append({"type": "edit_object", "target": target_id, "changes": effect.changes})
        elif effect.effect_type == "create_object":
            type_id = effect.target
            data = effect.changes or params
            inst = self.store.create(type_id, data)
            effects_applied.append({"type": "create_object", "instance_id": inst.instance_id})
        elif effect.effect_type == "create_link":
            link_type_id = effect.target
            source_id = effect.changes.get("source_id") or params.get("source_id") or params.get("asset_id")
            target_id = effect.changes.get("target_id") or params.get("target_id") or params.get("tech_id")
            if source_id and target_id:
                self.store.create_link(link_type_id, source_id, target_id)
                effects_applied.append({"type": "create_link", "link_type_id": link_type_id, "source": source_id, "target": target_id})
        elif effect.effect_type == "delete_link":
            # Simplified: would need link identity
            effects_applied.append({"type": "delete_link", "target": effect.target})
        elif effect.effect_type == "delete_object":
            target_id = effect.changes.get("instance_id") or params.get("instance_id")
            if target_id:
                self.store.delete(target_id)
                effects_applied.append({"type": "delete_object", "instance_id": target_id})
        elif effect.effect_type == "notification":
            effects_applied.append({"type": "notification", "target": effect.target, "message": effect.changes.get("message", "")})
