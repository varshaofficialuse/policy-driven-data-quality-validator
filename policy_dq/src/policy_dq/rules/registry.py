"""Registries mapping rule_type strings to validator classes."""
from policy_dq.validators.base import BaseValidator
from policy_dq.rules.validators import (
    CrossFieldCheck,
    RangeCheck,
    RegexCheck,
    RequiredField,
    TypeCheck,
    UniquenessCheck,
)

RULE_REGISTRY: dict[str, type[BaseValidator]] = {
    "required":   RequiredField,
    "type_check": TypeCheck,
    "regex":      RegexCheck,
    "range":      RangeCheck,
    "unique":     UniquenessCheck,
}

CROSS_FIELD_REGISTRY: dict[str, type[CrossFieldCheck]] = {
    "cross_field": CrossFieldCheck,
}
