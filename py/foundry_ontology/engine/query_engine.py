"""Chainable query interface — navigate ontology links, not SQL joins."""

from typing import Any, Optional

from foundry_ontology.engine.object_store import ObjectInstance, ObjectStore


class OntologyQuery:
    """Chainable query — equivalent to Foundry's Objects.search() API."""

    def __init__(
        self,
        store: ObjectStore,
        type_id: str,
        filters: Optional[dict[str, Any]] = None,
        path: Optional[list[tuple[str, Optional[str], dict]]] = None,
    ):
        # path: [(type_id, link_type_id, filters), ...] for each step
        self._store = store
        self._type_id = type_id
        self._filters = filters or {}
        self._path = path or [(type_id, None, self._filters)]
        self._order_by: Optional[tuple[str, str]] = None
        self._take_limit: Optional[int] = None

    def filter(self, **kwargs: Any) -> "OntologyQuery":
        """Add property filters to current step."""
        new_filters = {**self._filters, **kwargs}
        last_link = self._path[-1][1] if self._path else None
        new_path = self._path[:-1] + [(self._type_id, last_link, new_filters)]
        q = OntologyQuery(self._store, self._type_id, new_filters, new_path)
        q._order_by = self._order_by
        q._take_limit = self._take_limit
        return q

    def navigate(self, link_type_id: str) -> "OntologyQuery":
        """Follow a link to the target type."""
        lt = self._store.ontology.link_types.get(link_type_id)
        if not lt:
            raise ValueError(f"Unknown link type: {link_type_id}")
        new_path = self._path + [(lt.target_type, link_type_id, {})]
        q = OntologyQuery(self._store, lt.target_type, {}, new_path)
        q._order_by = self._order_by
        q._take_limit = self._take_limit
        return q

    def order_by(self, prop: str, direction: str = "asc") -> "OntologyQuery":
        """Order results by property."""
        q = OntologyQuery(self._store, self._type_id, self._filters, self._path)
        q._order_by = (prop, direction.lower())
        q._take_limit = self._take_limit
        return q

    def take(self, n: int) -> list[ObjectInstance]:
        """Limit and execute query, return up to n results."""
        q = OntologyQuery(self._store, self._type_id, self._filters, self._path)
        q._order_by = self._order_by
        q._take_limit = n
        return q.all()[:n]

    def _execute(self) -> list[ObjectInstance]:
        """Execute the query and return results."""
        items: list[ObjectInstance] = []
        for i, (type_id, link_type_id, filters) in enumerate(self._path):
            if i == 0:
                items = self._store.search(type_id, filters)
            else:
                # Navigate from previous step using current step's link
                link_id = link_type_id
                if link_id:
                    new_items = []
                    seen = set()
                    for src in items:
                        for tgt in self._store.get_linked(src.instance_id, link_id):
                            if tgt.instance_id not in seen and all(
                                tgt.properties.get(k) == v for k, v in filters.items()
                            ):
                                new_items.append(tgt)
                                seen.add(tgt.instance_id)
                    items = new_items
                else:
                    items = [x for x in items if all(x.properties.get(k) == v for k, v in filters.items())]

        if self._order_by:
            prop, direction = self._order_by
            reverse = direction == "desc"
            items = sorted(
                items,
                key=lambda x: (x.properties.get(prop) is None, x.properties.get(prop)),
                reverse=reverse,
            )
        if self._take_limit is not None:
            items = items[: self._take_limit]
        return items

    def all(self) -> list[ObjectInstance]:
        """Execute and return all results."""
        return self._execute()

    def first(self) -> Optional[ObjectInstance]:
        """Execute and return first result."""
        items = self.take(1)
        return items[0] if items else None

    def count(self) -> int:
        """Return count of matching results."""
        return len(self._execute())


def objects(store: ObjectStore, type_id: str) -> OntologyQuery:
    """Start a query for the given type. Mirrors query.objects('Asset')."""
    return OntologyQuery(store, type_id)
