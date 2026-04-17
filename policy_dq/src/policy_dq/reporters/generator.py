import json
from pathlib import Path

from policy_dq.models import ValidationResult


class ReportGenerator:
    """Generates JSON and Markdown reports from a ValidationResult."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result

    def to_json(self, path: str | Path) -> None:
        """Save the full ValidationResult as a JSON file."""
        Path(path).write_text(
            json.dumps(self.result.model_dump(), indent=2),
            encoding="utf-8",
        )

    def to_markdown(self, path: str | Path) -> None:
        """Save a human-readable Markdown summary of validation issues."""
        lines: list[str] = []
        status = "✅ PASSED" if self.result.is_valid else "❌ FAILED"
        lines.append(f"# Validation Report — {status}\n")

        if self.result.metadata:
            lines.append("## Summary\n")
            for key, value in self.result.metadata.items():
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")

        if self.result.is_valid:
            lines.append("No issues found.")
        else:
            lines.append("## Issues\n")
            lines.append("| Row | Field | Rule | Message |")
            lines.append("|-----|-------|------|---------|")
            for issue in self.result.issues:
                row = str(issue.row_index) if issue.row_index is not None else "—"
                lines.append(f"| {row} | `{issue.field_name}` | `{issue.rule_type}` | {issue.message} |")

        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
