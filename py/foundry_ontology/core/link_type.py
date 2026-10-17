"""LinkType definitions — relationships between ObjectTypes."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from foundry_ontology.core.object_type import Property


class Cardinality(Enum):
    """Relationship cardinality."""

    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


@dataclass
class LinkType:
    """A typed relationship between two ObjectTypes."""

    link_id: str
    display_name: str
    description: str = ""
    source_type: str = ""
    target_type: str = ""
    cardinality: Cardinality = Cardinality.ONE_TO_MANY
    reverse_name: Optional[str] = None
    properties: dict[str, Property] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
