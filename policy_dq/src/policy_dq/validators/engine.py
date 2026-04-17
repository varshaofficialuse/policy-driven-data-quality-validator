import pandas as pd

from policy_dq.models import Rule, ValidationIssue, ValidationResult
from policy_dq.rules.registry import CROSS_FIELD_REGISTRY, RULE_REGISTRY


class ValidationEngine:
    """Runs a list of Rules against a Pandas DataFrame."""

    def __init__(self, df: pd.DataFrame, rules: list[Rule]) -> None:
        self.df = df
        self.rules = rules

    def run(self) -> ValidationResult:
        """Execute all rules and return a ValidationResult."""
        all_issues: list[ValidationIssue] = []

        for rule in self.rules:
            if rule.rule_type in CROSS_FIELD_REGISTRY:
                validator = CROSS_FIELD_REGISTRY[rule.rule_type](rule)
                all_issues.extend(validator.validate(self.df))
                continue

            validator_cls = RULE_REGISTRY.get(rule.rule_type)
            if validator_cls is None:
                raise ValueError(
                    f"Unknown rule_type '{rule.rule_type}'. "
                    f"Available: {list(RULE_REGISTRY) + list(CROSS_FIELD_REGISTRY)}"
                )

            if rule.field_name not in self.df.columns:
                all_issues.append(ValidationIssue(
                    field_name=rule.field_name,
                    rule_type=rule.rule_type,
                    message=f"Column '{rule.field_name}' not found in DataFrame.",
                ))
                continue

            validator = validator_cls(rule)
            all_issues.extend(validator.validate(self.df[rule.field_name]))

        # Deterministic ordering: row_index asc (nulls last), then field_name asc
        all_issues.sort(key=lambda i: (
            i.row_index if i.row_index is not None else float("inf"),
            i.field_name,
        ))

        return ValidationResult(
            is_valid=len(all_issues) == 0,
            errors=[i.message for i in all_issues],
            issues=all_issues,
            metadata={"total_rules": len(self.rules), "total_issues": len(all_issues)},
        )
