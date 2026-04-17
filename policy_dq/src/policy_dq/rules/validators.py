import re
from datetime import datetime

import pandas as pd

from policy_dq.models import Rule, ValidationIssue
from policy_dq.validators.base import BaseValidator

_TYPE_MAP: dict[str, type] = {"int": int, "float": float, "str": str}


class RequiredField(BaseValidator):
    """Fails for any null or empty-string value."""

    def validate(self, series: pd.Series) -> list[ValidationIssue]:
        """Check that every value is non-null and non-empty."""
        issues: list[ValidationIssue] = []
        for idx, value in series.items():
            if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name,
                    rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' is required but missing.",
                ))
        return issues


class TypeCheck(BaseValidator):
    """Fails when a value cannot be cast to the expected Python type.

    params:
        expected_type: one of "int", "float", "str"
    """

    def validate(self, series: pd.Series) -> list[ValidationIssue]:
        """Check that every value is castable to the expected type."""
        expected = self.rule.params.get("expected_type", "str")
        target_type = _TYPE_MAP.get(expected)
        if target_type is None:
            raise ValueError(f"Unsupported expected_type '{expected}'. Choose from {list(_TYPE_MAP)}")

        issues: list[ValidationIssue] = []
        for idx, value in series.items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            try:
                target_type(value)
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name,
                    rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' value {value!r} cannot be cast to {expected}.",
                ))
        return issues


class RegexCheck(BaseValidator):
    """Fails when a string value does not match the given pattern.

    params:
        pattern: regex pattern string
    """

    def validate(self, series: pd.Series) -> list[ValidationIssue]:
        """Check that every value matches the regex pattern."""
        pattern = self.rule.params.get("pattern")
        if not pattern:
            raise ValueError("RegexCheck requires a 'pattern' param.")
        compiled = re.compile(pattern)

        issues: list[ValidationIssue] = []
        for idx, value in series.items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            if not compiled.fullmatch(str(value)):
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name,
                    rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' value {value!r} does not match pattern '{pattern}'.",
                ))
        return issues


class RangeCheck(BaseValidator):
    """Fails when a numeric value falls outside [min, max].

    params:
        min: lower bound inclusive (optional)
        max: upper bound inclusive (optional)
    """

    def validate(self, series: pd.Series) -> list[ValidationIssue]:
        """Check that every numeric value is within the configured bounds."""
        min_val = self.rule.params.get("min")
        max_val = self.rule.params.get("max")

        issues: list[ValidationIssue] = []
        for idx, value in series.items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            try:
                num = float(value)
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name,
                    rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' value {value!r} is not numeric.",
                ))
                continue

            if min_val is not None and num < min_val:
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name,
                    rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' value {num} is below minimum {min_val}.",
                ))
            elif max_val is not None and num > max_val:
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name,
                    rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' value {num} exceeds maximum {max_val}.",
                ))
        return issues


class UniquenessCheck(BaseValidator):
    """Fails for any duplicate values in the column."""

    def validate(self, series: pd.Series) -> list[ValidationIssue]:
        """Check that all values in the column are unique."""
        duplicates = series[series.duplicated(keep=False)]
        return [
            ValidationIssue(
                field_name=self.rule.field_name,
                rule_type=self.rule.rule_type,
                row_index=int(idx),  # type: ignore[arg-type]
                message=f"Row {idx}: '{self.rule.field_name}' value {value!r} is not unique.",
            )
            for idx, value in duplicates.items()
        ]


class CrossFieldCheck:
    """Checks a relationship between two columns.

    params:
        compare_field : name of the second column
        operator      : gt | gte | lt | lte  (default: gt)
        parse_dates   : parse values as ISO dates before comparing
    """

    def __init__(self, rule: Rule) -> None:
        self.rule = rule

    def validate(self, df: pd.DataFrame) -> list[ValidationIssue]:
        """Check the cross-field relationship for every row."""
        compare_field = self.rule.params.get("compare_field")
        if not compare_field:
            raise ValueError("CrossFieldCheck requires a 'compare_field' param.")

        operator = self.rule.params.get("operator", "gt")
        parse_dates = self.rule.params.get("parse_dates", False)

        if self.rule.field_name not in df.columns:
            return [ValidationIssue(
                field_name=self.rule.field_name, rule_type=self.rule.rule_type,
                message=f"Column '{self.rule.field_name}' not found in DataFrame.",
            )]
        if compare_field not in df.columns:
            return [ValidationIssue(
                field_name=self.rule.field_name, rule_type=self.rule.rule_type,
                message=f"compare_field column '{compare_field}' not found in DataFrame.",
            )]

        _ops = {"gt": lambda a, b: a > b, "gte": lambda a, b: a >= b,
                "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b}
        op_fn = _ops.get(operator)
        if op_fn is None:
            raise ValueError(f"Unsupported operator '{operator}'. Choose from {list(_ops)}.")

        issues: list[ValidationIssue] = []
        for idx, row in df.iterrows():
            a, b = row[self.rule.field_name], row[compare_field]
            if a is None or b is None:
                continue
            if isinstance(a, float) and pd.isna(a):
                continue
            if isinstance(b, float) and pd.isna(b):
                continue
            if parse_dates:
                try:
                    a = datetime.fromisoformat(str(a))
                    b = datetime.fromisoformat(str(b))
                except ValueError:
                    issues.append(ValidationIssue(
                        field_name=self.rule.field_name, rule_type=self.rule.rule_type,
                        row_index=int(idx),  # type: ignore[arg-type]
                        message=f"Row {idx}: could not parse dates ('{self.rule.field_name}'='{a}', '{compare_field}'='{b}').",
                    ))
                    continue
            if not op_fn(a, b):
                issues.append(ValidationIssue(
                    field_name=self.rule.field_name, rule_type=self.rule.rule_type,
                    row_index=int(idx),  # type: ignore[arg-type]
                    message=f"Row {idx}: '{self.rule.field_name}' ({a!r}) must be {operator} '{compare_field}' ({b!r}).",
                ))
        return issues
