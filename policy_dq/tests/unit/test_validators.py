"""Unit tests for all concrete validator classes."""
import pandas as pd
import pytest

from policy_dq.models import Rule
from policy_dq.rules.validators import (
    CrossFieldCheck, RangeCheck, RegexCheck,
    RequiredField, TypeCheck, UniquenessCheck,
)


def make_series(values: list, name: str = "field") -> pd.Series:
    """Build a named Series from a plain list."""
    return pd.Series(values, name=name)


def make_rule(rule_type: str, field: str = "field", **params) -> Rule:
    """Build a Rule with arbitrary params."""
    return Rule(field_name=field, rule_type=rule_type, params=params)


class TestRequiredField:
    def test_all_present_passes(self):
        assert RequiredField(make_rule("required", "name")).validate(make_series(["Alice", "Bob"], "name")) == []

    def test_none_fails(self):
        issues = RequiredField(make_rule("required", "name")).validate(make_series([None, "Bob"], "name"))
        assert len(issues) == 1 and issues[0].row_index == 0

    def test_empty_string_fails(self):
        assert len(RequiredField(make_rule("required", "name")).validate(make_series(["", "Bob"], "name"))) == 1

    def test_nan_fails(self):
        assert len(RequiredField(make_rule("required", "name")).validate(make_series([float("nan"), "Bob"], "name"))) == 1


class TestTypeCheck:
    def test_valid_ints_pass(self):
        assert TypeCheck(make_rule("type_check", "age", expected_type="int")).validate(make_series([1, 2, 3], "age")) == []

    def test_non_int_string_fails(self):
        issues = TypeCheck(make_rule("type_check", "age", expected_type="int")).validate(make_series(["abc", 2], "age"))
        assert len(issues) == 1 and issues[0].row_index == 0

    def test_nulls_skipped(self):
        assert TypeCheck(make_rule("type_check", "age", expected_type="int")).validate(make_series([None, 5], "age")) == []

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            TypeCheck(make_rule("type_check", "x", expected_type="bool")).validate(make_series([True]))


class TestRegexCheck:
    def test_valid_emails_pass(self):
        assert RegexCheck(make_rule("regex", "email", pattern=r"[^@]+@[^@]+\.[^@]+")).validate(make_series(["a@b.com"], "email")) == []

    def test_invalid_email_fails(self):
        issues = RegexCheck(make_rule("regex", "email", pattern=r"[^@]+@[^@]+\.[^@]+")).validate(make_series(["bad", "a@b.com"], "email"))
        assert len(issues) == 1 and issues[0].row_index == 0

    def test_custom_pattern(self):
        issues = RegexCheck(make_rule("regex", "code", pattern=r"\d{4}")).validate(make_series(["1234", "12AB"], "code"))
        assert len(issues) == 1 and issues[0].row_index == 1

    def test_null_skipped(self):
        assert RegexCheck(make_rule("regex", "email", pattern=r"[^@]+@[^@]+\.[^@]+")).validate(make_series([None, "a@b.com"], "email")) == []

    def test_missing_pattern_raises(self):
        with pytest.raises(ValueError, match="pattern"):
            RegexCheck(make_rule("regex", "email")).validate(make_series(["a@b.com"]))


class TestRangeCheck:
    def test_within_range_passes(self):
        assert RangeCheck(make_rule("range", "age", min=18, max=65)).validate(make_series([18, 30, 65], "age")) == []

    def test_below_minimum_fails(self):
        issues = RangeCheck(make_rule("range", "age", min=18)).validate(make_series([17, 18, 25], "age"))
        assert len(issues) == 1 and "below minimum" in issues[0].message

    def test_above_maximum_fails(self):
        issues = RangeCheck(make_rule("range", "score", max=100)).validate(make_series([50, 101, 99], "score"))
        assert len(issues) == 1 and "exceeds maximum" in issues[0].message

    def test_multiple_violations(self):
        assert len(RangeCheck(make_rule("range", "val", min=0, max=10)).validate(make_series([-1, 5, 11, 3], "val"))) == 2

    def test_null_skipped(self):
        assert RangeCheck(make_rule("range", "val", min=0)).validate(make_series([None, 5], "val")) == []

    def test_non_numeric_reported(self):
        issues = RangeCheck(make_rule("range", "val", min=0)).validate(make_series(["abc", 5], "val"))
        assert len(issues) == 1 and "not numeric" in issues[0].message

    def test_only_min_bound(self):
        assert RangeCheck(make_rule("range", "price", min=0)).validate(make_series([0, 100], "price")) == []

    def test_only_max_bound(self):
        assert RangeCheck(make_rule("range", "pct", max=100)).validate(make_series([0, 100], "pct")) == []


class TestUniquenessCheck:
    def test_unique_passes(self):
        assert UniquenessCheck(make_rule("unique", "id")).validate(make_series([1, 2, 3], "id")) == []

    def test_duplicates_fail(self):
        issues = UniquenessCheck(make_rule("unique", "id")).validate(make_series([1, 2, 1], "id"))
        assert len(issues) == 2


class TestCrossFieldCheck:
    def _df(self, start: list, end: list) -> pd.DataFrame:
        return pd.DataFrame({"start_date": start, "end_date": end})

    def test_end_after_start_passes(self):
        rule = make_rule("cross_field", "end_date", compare_field="start_date", operator="gt")
        assert CrossFieldCheck(rule).validate(self._df([1, 2], [2, 3])) == []

    def test_end_before_start_fails(self):
        rule = make_rule("cross_field", "end_date", compare_field="start_date", operator="gt")
        issues = CrossFieldCheck(rule).validate(self._df([5, 1], [3, 2]))
        assert len(issues) == 1 and issues[0].row_index == 0

    def test_equal_fails_for_gt(self):
        rule = make_rule("cross_field", "end_date", compare_field="start_date", operator="gt")
        assert len(CrossFieldCheck(rule).validate(self._df([5], [5]))) == 1

    def test_equal_passes_for_gte(self):
        rule = make_rule("cross_field", "end_date", compare_field="start_date", operator="gte")
        assert CrossFieldCheck(rule).validate(self._df([5], [5])) == []

    def test_iso_dates_pass(self):
        rule = make_rule("cross_field", "end_date", compare_field="start_date", operator="gt", parse_dates=True)
        assert CrossFieldCheck(rule).validate(self._df(["2024-01-01"], ["2024-06-01"])) == []

    def test_iso_dates_violation(self):
        rule = make_rule("cross_field", "end_date", compare_field="start_date", operator="gt", parse_dates=True)
        assert len(CrossFieldCheck(rule).validate(self._df(["2024-06-01"], ["2024-01-01"]))) == 1

    def test_missing_compare_field_raises(self):
        with pytest.raises(ValueError, match="compare_field"):
            CrossFieldCheck(make_rule("cross_field", "end_date")).validate(self._df([1], [2]))

    def test_column_not_found(self):
        rule = make_rule("cross_field", "missing", compare_field="start_date", operator="gt")
        issues = CrossFieldCheck(rule).validate(self._df([1], [2]))
        assert len(issues) == 1 and "not found" in issues[0].message


class TestRuleParsing:
    def test_rule_from_dict(self):
        r = Rule(**{"field_name": "email", "rule_type": "regex", "params": {"pattern": r"\S+"}})
        assert r.field_name == "email" and r.params["pattern"] == r"\S+"

    def test_defaults_empty_params(self):
        assert Rule(field_name="name", rule_type="required").params == {}

    def test_missing_field_name_raises(self):
        with pytest.raises(Exception):
            Rule(rule_type="required")  # type: ignore[call-arg]


class TestDeterministicOrdering:
    def test_sorted_by_row_then_field(self):
        from policy_dq.validators.engine import ValidationEngine
        df = pd.DataFrame({"email": ["bad", "also-bad"], "age": [-1, -2]})
        rules = [
            Rule(field_name="email", rule_type="regex", params={"pattern": r"[^@]+@[^@]+\.[^@]+"}),
            Rule(field_name="age",   rule_type="range", params={"min": 0}),
        ]
        result = ValidationEngine(df, rules).run()
        indices = [i.row_index for i in result.issues]
        assert indices == sorted(indices)


class TestSeverityThreshold:
    def test_zero_threshold_fails_on_any_issue(self):
        from policy_dq.validators.engine import ValidationEngine
        df = pd.DataFrame({"age": [-1]})
        result = ValidationEngine(df, [Rule(field_name="age", rule_type="range", params={"min": 0})]).run()
        assert result.is_valid is False and result.metadata["total_issues"] == 1

    def test_threshold_counts(self):
        from policy_dq.validators.engine import ValidationEngine
        df = pd.DataFrame({"age": [-1, -2]})
        result = ValidationEngine(df, [Rule(field_name="age", rule_type="range", params={"min": 0})]).run()
        assert result.metadata["total_issues"] == 2
