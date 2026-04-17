"""Integration tests: full pipeline, CLI runner, and report output."""
import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from policy_dq.cli import cli
from policy_dq.models import Rule, ValidationResult
from policy_dq.parsers.factory import load_data
from policy_dq.reporters.generator import ReportGenerator
from policy_dq.validators.engine import ValidationEngine

VALID_CSV = textwrap.dedent("""\
    user_id,email,age,full_name
    1,alice@example.com,30,Alice Smith
    2,bob@example.com,25,Bob Jones
    3,carol@example.com,40,Carol White
""")

INVALID_CSV = textwrap.dedent("""\
    user_id,email,age,full_name
    1,alice@example.com,30,Alice Smith
    2,not-an-email,15,Bob Jones
    3,carol@example.com,40,
""")

RULES = [
    Rule(field_name="email",     rule_type="required"),
    Rule(field_name="email",     rule_type="regex",  params={"pattern": r"[^@]+@[^@]+\.[^@]+"}),
    Rule(field_name="age",       rule_type="range",  params={"min": 18, "max": 120}),
    Rule(field_name="full_name", rule_type="required"),
    Rule(field_name="user_id",   rule_type="unique"),
]

RULES_YAML = textwrap.dedent("""\
    - field_name: email
      rule_type: required
    - field_name: email
      rule_type: regex
      params:
        pattern: "[^@]+@[^@]+\\\\.[^@]+"
    - field_name: age
      rule_type: range
      params:
        min: 18
        max: 120
    - field_name: full_name
      rule_type: required
    - field_name: user_id
      rule_type: unique
""")


@pytest.fixture
def valid_csv(tmp_path: Path) -> Path:
    p = tmp_path / "valid.csv"
    p.write_text(VALID_CSV)
    return p


@pytest.fixture
def invalid_csv(tmp_path: Path) -> Path:
    p = tmp_path / "invalid.csv"
    p.write_text(INVALID_CSV)
    return p


@pytest.fixture
def rules_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "rules.yaml"
    p.write_text(RULES_YAML)
    return p


class TestLoader:
    def test_loads_csv(self, valid_csv: Path):
        df = load_data(valid_csv)
        assert list(df.columns) == ["user_id", "email", "age", "full_name"]
        assert len(df) == 3

    def test_loads_json(self, tmp_path: Path):
        p = tmp_path / "data.json"
        p.write_text('[{"id": 1, "val": "x"}, {"id": 2, "val": "y"}]')
        assert len(load_data(p)) == 2

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_data(tmp_path / "missing.csv")

    def test_unsupported_extension(self, tmp_path: Path):
        p = tmp_path / "data.xlsx"
        p.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported"):
            load_data(p)


class TestPipelineValid:
    def test_passes_clean_data(self, valid_csv: Path):
        result = ValidationEngine(load_data(valid_csv), RULES).run()
        assert result.is_valid is True and result.issues == []

    def test_metadata_rule_count(self, valid_csv: Path):
        result = ValidationEngine(load_data(valid_csv), RULES).run()
        assert result.metadata["total_rules"] == len(RULES)


class TestPipelineInvalid:
    def test_detects_bad_email(self, invalid_csv: Path):
        result = ValidationEngine(load_data(invalid_csv), RULES).run()
        assert result.is_valid is False
        assert any(i.rule_type == "regex" for i in result.issues)

    def test_detects_underage(self, invalid_csv: Path):
        result = ValidationEngine(load_data(invalid_csv), RULES).run()
        assert any("below minimum" in i.message for i in result.issues)

    def test_detects_missing_full_name(self, invalid_csv: Path):
        result = ValidationEngine(load_data(invalid_csv), RULES).run()
        assert any(i.field_name == "full_name" and i.rule_type == "required" for i in result.issues)

    def test_errors_match_issues(self, invalid_csv: Path):
        result = ValidationEngine(load_data(invalid_csv), RULES).run()
        assert len(result.errors) == len(result.issues)

    def test_deterministic_ordering(self, invalid_csv: Path):
        r1 = ValidationEngine(load_data(invalid_csv), RULES).run()
        r2 = ValidationEngine(load_data(invalid_csv), RULES).run()
        assert [i.message for i in r1.issues] == [i.message for i in r2.issues]


class TestLocalRulesLoading:
    def test_yaml_rules_load_and_run(self, valid_csv: Path, rules_yaml: Path):
        from policy_dq.cli import _load_rules_from_file
        rules = _load_rules_from_file(str(rules_yaml))
        assert len(rules) == 5
        assert ValidationEngine(load_data(valid_csv), rules).run().is_valid is True

    def test_json_rules_load(self, tmp_path: Path):
        from policy_dq.cli import _load_rules_from_file
        p = tmp_path / "rules.json"
        p.write_text('[{"field_name": "age", "rule_type": "range", "params": {"min": 0}}]')
        rules = _load_rules_from_file(str(p))
        assert len(rules) == 1 and rules[0].rule_type == "range"


class TestMCPRulesMocked:
    def test_mocked_fetch_runs_correctly(self, valid_csv: Path):
        with patch("policy_dq.mcp.client.fetch_rules", return_value=RULES):
            from policy_dq.mcp.client import fetch_rules
            rules = fetch_rules("onboarding")
        assert ValidationEngine(load_data(valid_csv), rules).run().is_valid is True


class TestCLIValidate:
    def test_success_exits_zero(self, valid_csv: Path, rules_yaml: Path):
        result = CliRunner().invoke(cli, ["validate", str(valid_csv), "--rules", str(rules_yaml)])
        assert result.exit_code == 0 and "✅" in result.output

    def test_failure_exits_nonzero(self, invalid_csv: Path, rules_yaml: Path):
        result = CliRunner().invoke(cli, ["validate", str(invalid_csv), "--rules", str(rules_yaml)])
        assert result.exit_code == 1 and "❌" in result.output

    def test_output_dir_creates_reports(self, valid_csv: Path, rules_yaml: Path, tmp_path: Path):
        out = tmp_path / "reports"
        CliRunner().invoke(cli, ["validate", str(valid_csv), "--rules", str(rules_yaml), "--output-dir", str(out)])
        assert (out / "report.json").exists() and (out / "report.md").exists()

    def test_threshold_allows_issues(self, invalid_csv: Path, rules_yaml: Path):
        result = CliRunner().invoke(cli, ["validate", str(invalid_csv), "--rules", str(rules_yaml), "--threshold", "100"])
        assert result.exit_code == 0 and "✅" in result.output

    def test_missing_rules_errors(self, valid_csv: Path):
        assert CliRunner().invoke(cli, ["validate", str(valid_csv)]).exit_code != 0

    def test_file_not_found_errors(self, rules_yaml: Path):
        assert CliRunner().invoke(cli, ["validate", "nonexistent.csv", "--rules", str(rules_yaml)]).exit_code != 0


class TestCLISummarize:
    def test_summarize_passed(self, valid_csv: Path, tmp_path: Path):
        report = tmp_path / "report.json"
        ReportGenerator(ValidationEngine(load_data(valid_csv), RULES).run()).to_json(report)
        out = CliRunner().invoke(cli, ["summarize", str(report)])
        assert out.exit_code == 0 and "PASSED" in out.output

    def test_summarize_failed(self, invalid_csv: Path, tmp_path: Path):
        report = tmp_path / "report.json"
        ReportGenerator(ValidationEngine(load_data(invalid_csv), RULES).run()).to_json(report)
        out = CliRunner().invoke(cli, ["summarize", str(report)])
        assert out.exit_code == 0 and "FAILED" in out.output

    def test_missing_file_errors(self):
        assert CliRunner().invoke(cli, ["summarize", "nonexistent.json"]).exit_code != 0


class TestReportGeneration:
    def test_json_report_structure(self, invalid_csv: Path, tmp_path: Path):
        result = ValidationEngine(load_data(invalid_csv), RULES).run()
        out = tmp_path / "report.json"
        ReportGenerator(result).to_json(out)
        data = json.loads(out.read_text())
        assert data["is_valid"] is False and len(data["issues"]) > 0

    def test_markdown_failed(self, invalid_csv: Path, tmp_path: Path):
        result = ValidationEngine(load_data(invalid_csv), RULES).run()
        out = tmp_path / "report.md"
        ReportGenerator(result).to_markdown(out)
        content = out.read_text()
        assert "❌ FAILED" in content and "| Row |" in content

    def test_markdown_passed(self, valid_csv: Path, tmp_path: Path):
        result = ValidationEngine(load_data(valid_csv), RULES).run()
        out = tmp_path / "report.md"
        ReportGenerator(result).to_markdown(out)
        assert "✅ PASSED" in out.read_text()
