from typing import Any
from pydantic import BaseModel


class Rule(BaseModel):
    """A single validation rule applied to a field."""
    field_name: str
    rule_type: str  # e.g. "required", "regex", "range", "unique", "cross_field"
    params: dict[str, Any] = {}


class ValidationIssue(BaseModel):
    """A single validation violation."""
    field_name: str
    rule_type: str
    row_index: int | None = None  # None for column-level checks
    message: str


class ValidationResult(BaseModel):
    """Aggregated result of a full validation run."""
    is_valid: bool
    errors: list[str] = []
    issues: list[ValidationIssue] = []
    metadata: dict[str, Any] = {}
