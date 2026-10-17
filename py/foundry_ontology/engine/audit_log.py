"""Immutable audit trail for all actions."""

import csv
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AuditEntry:
    """A single audit log entry."""

    entry_id: str
    timestamp: datetime
    action_type_id: str
    executed_by: str
    parameters: dict
    effects: list[dict]
    success: bool
    error_message: Optional[str] = None


class AuditLog:
    """Immutable audit trail — equivalent to Foundry's action audit."""

    def __init__(self):
        self._entries: dict[str, AuditEntry] = {}

    def append(self, entry: AuditEntry) -> str:
        """Append an entry and return its ID."""
        if not entry.entry_id:
            entry = AuditEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=entry.timestamp,
                action_type_id=entry.action_type_id,
                executed_by=entry.executed_by,
                parameters=entry.parameters,
                effects=entry.effects,
                success=entry.success,
                error_message=entry.error_message,
            )
        self._entries[entry.entry_id] = entry
        return entry.entry_id

    def get(self, entry_id: str) -> Optional[AuditEntry]:
        """Get an entry by ID."""
        return self._entries.get(entry_id)

    def query(
        self,
        action_type_id: Optional[str] = None,
        user: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
    ) -> list[AuditEntry]:
        """Query entries by filters."""
        result = list(self._entries.values())
        if action_type_id:
            result = [e for e in result if e.action_type_id == action_type_id]
        if user:
            result = [e for e in result if e.executed_by == user]
        if after:
            result = [e for e in result if e.timestamp >= after]
        if before:
            result = [e for e in result if e.timestamp <= before]
        result.sort(key=lambda e: e.timestamp, reverse=True)
        return result

    def export_csv(self, path: str) -> None:
        """Export all entries to CSV."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                ["entry_id", "timestamp", "action_type_id", "executed_by", "success", "error_message"]
            )
            for e in sorted(self._entries.values(), key=lambda x: x.timestamp):
                w.writerow(
                    [
                        e.entry_id,
                        e.timestamp.isoformat(),
                        e.action_type_id,
                        e.executed_by,
                        e.success,
                        e.error_message or "",
                    ]
                )
