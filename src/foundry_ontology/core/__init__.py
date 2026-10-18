"""Core ontology primitives: ObjectType, Property, LinkType, ActionType, Function, Interface."""

from foundry_ontology.core.data_types import PropertyType, ValueType
from foundry_ontology.core.object_type import ObjectType, Property, SharedProperty, ValidationResult
from foundry_ontology.core.link_type import Cardinality, LinkType
from foundry_ontology.core.action_type import (
    ActionEffect,
    ActionParameter,
    ActionType,
    ValidationRule,
)
from foundry_ontology.core.function import OntologyFunction
from foundry_ontology.core.interface import Interface
from foundry_ontology.core.ontology import Ontology

__all__ = [
    "PropertyType",
    "ValueType",
    "Property",
    "SharedProperty",
    "ValidationResult",
    "ObjectType",
    "Cardinality",
    "LinkType",
    "ActionParameter",
    "ValidationRule",
    "ActionEffect",
    "ActionType",
    "OntologyFunction",
    "Interface",
    "Ontology",
]
