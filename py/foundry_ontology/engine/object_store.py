"""In-memory object store with SQLite persistence — equivalent to Foundry Object Storage V2."""

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from foundry_ontology.core import Ontology


@dataclass
class ObjectInstance:
    """An instance of an ObjectType."""

    instance_id: str
    object_type_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    links: dict[str, list[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    version: int = 1


class ObjectStore:
    """In-memory store for object instances with optional SQLite persistence."""

    def __init__(self, ontology: Ontology, db_path: str = ":memory:"):
        self.ontology = ontology
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        # ★★★ 我方改动（2026-10-17）：允许跨线程 —— ★ 本体在【主线程】建 store，
        #   而 zenoh 的回调在【别的线程】跑 ⇒ 不放开就报「SQLite objects created in a thread...」
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.Lock()   # ★ 跨线程了，就要加锁
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS objects (
                instance_id TEXT PRIMARY KEY,
                object_type_id TEXT NOT NULL,
                properties TEXT,
                links TEXT,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT,
                version INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS link_table (
                link_type_id TEXT,
                source_id TEXT,
                target_id TEXT,
                PRIMARY KEY (link_type_id, source_id, target_id)
            );
        """)
        self._conn.commit()
        self._load_to_memory()

    def _load_to_memory(self) -> None:
        self._objects: dict[str, ObjectInstance] = {}
        self._links: dict[str, list[tuple[str, str]]] = {}  # link_type_id -> [(source, target), ...]
        if self._conn:
            for row in self._conn.execute("SELECT * FROM objects"):
                inst = ObjectInstance(
                    instance_id=row[0],
                    object_type_id=row[1],
                    properties=json.loads(row[2] or "{}"),
                    links=json.loads(row[3] or "{}"),
                    created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    created_by=row[6] or "",
                    version=row[7] or 1,
                )
                self._objects[inst.instance_id] = inst
            for row in self._conn.execute("SELECT link_type_id, source_id, target_id FROM link_table"):
                k = row[0]
                if k not in self._links:
                    self._links[k] = []
                self._links[k].append((row[1], row[2]))
            # Rebuild links in each object from link_table
            for link_type_id, pairs in self._links.items():
                for src_id, tgt_id in pairs:
                    obj = self._objects.get(src_id)
                    if obj:
                        if link_type_id not in obj.links:
                            obj.links[link_type_id] = []
                        if tgt_id not in obj.links[link_type_id]:
                            obj.links[link_type_id].append(tgt_id)

    def _persist(self, inst: ObjectInstance) -> None:
        if self._conn and self.db_path != ":memory:":
            self._conn.execute(
                """INSERT OR REPLACE INTO objects
                   (instance_id, object_type_id, properties, links, created_at, updated_at, created_by, version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    inst.instance_id,
                    inst.object_type_id,
                    json.dumps(inst.properties),
                    json.dumps(inst.links),
                    inst.created_at.isoformat(),
                    inst.updated_at.isoformat(),
                    inst.created_by,
                    inst.version,
                ),
            )
            self._conn.commit()

    def create(self, type_id: str, data: dict[str, Any], created_by: str = "") -> ObjectInstance:
        """Create a new object instance."""
        ot = self.ontology.object_types.get(type_id)
        if not ot:
            raise ValueError(f"Unknown object type: {type_id}")
        result = ot.validate_instance(data)
        if not result.valid:
            raise ValueError(f"Validation failed: {result.errors}")
        inst = ObjectInstance(
            instance_id=data.get(ot.primary_key) or str(uuid.uuid4()),
            object_type_id=type_id,
            properties=dict(data),
            created_by=created_by,
        )
        if ot.primary_key and ot.primary_key not in inst.properties:
            inst.properties[ot.primary_key] = inst.instance_id
        self._objects[inst.instance_id] = inst
        self._persist(inst)
        return inst

    def get(self, instance_id: str) -> Optional[ObjectInstance]:
        """Get an instance by ID."""
        return self._objects.get(instance_id)

    def update(
        self, instance_id: str, changes: dict[str, Any], updated_by: str = ""
    ) -> Optional[ObjectInstance]:
        """Update an instance."""
        inst = self._objects.get(instance_id)
        if not inst:
            return None
        ot = self.ontology.object_types.get(inst.object_type_id)
        if ot:
            merged = {**inst.properties, **changes}
            result = ot.validate_instance(merged)
            if not result.valid:
                raise ValueError(f"Validation failed: {result.errors}")
            inst.properties = merged
        else:
            inst.properties.update(changes)
        inst.updated_at = datetime.now()
        inst.version += 1
        self._persist(inst)
        return inst

    def delete(self, instance_id: str, deleted_by: str = "") -> bool:
        """Delete an instance."""
        if instance_id not in self._objects:
            return False
        del self._objects[instance_id]
        if self._conn:
            self._conn.execute("DELETE FROM objects WHERE instance_id = ?", (instance_id,))
            self._conn.execute("DELETE FROM link_table WHERE source_id = ? OR target_id = ?", (instance_id, instance_id))
            self._conn.commit()
        return True

    def search(self, type_id: str, filters: Optional[dict[str, Any]] = None) -> list[ObjectInstance]:
        """Search instances by type and filters."""
        filters = filters or {}
        result = [
            inst
            for inst in self._objects.values()
            if inst.object_type_id == type_id
            and all(inst.properties.get(k) == v for k, v in filters.items())
        ]
        return result

    def create_link(
        self, link_type_id: str, source_id: str, target_id: str
    ) -> bool:
        """Create a link between instances."""
        if source_id not in self._objects or target_id not in self._objects:
            return False
        lt = self.ontology.link_types.get(link_type_id)
        if not lt:
            return False
        if link_type_id not in self._links:
            self._links[link_type_id] = []
        if (source_id, target_id) in self._links[link_type_id]:
            return True  # idempotent
        self._links[link_type_id].append((source_id, target_id))
        src = self._objects[source_id]
        key = link_type_id
        if key not in src.links:
            src.links[key] = []
        if target_id not in src.links[key]:
            src.links[key].append(target_id)
        self._persist(src)
        if self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO link_table (link_type_id, source_id, target_id) VALUES (?, ?, ?)",
                (link_type_id, source_id, target_id),
            )
            self._conn.commit()
        return True

    def get_linked(
        self, instance_id: str, link_type_id: str
    ) -> list[ObjectInstance]:
        """Get instances linked from this one via the given link type."""
        inst = self._objects.get(instance_id)
        if not inst:
            return []
        target_ids = inst.links.get(link_type_id, [])
        return [o for o in (self._objects.get(t) for t in target_ids) if o is not None]

    def count(self, type_id: str, filters: Optional[dict[str, Any]] = None) -> int:
        """Count instances by type and filters."""
        return len(self.search(type_id, filters))

    def get_all_instances(self) -> list[ObjectInstance]:
        """Get all object instances (for export)."""
        return list(self._objects.values())
