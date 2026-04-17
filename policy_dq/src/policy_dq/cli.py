import json
from pathlib import Path

import click
import yaml

from policy_dq.models import Rule
from policy_dq.parsers.factory import load_data
from policy_dq.reporters.generator import ReportGenerator
from policy_dq.validators.engine import ValidationEngine


def _load_rules_from_file(rules_path: str) -> list[Rule]:
    """Parse a local JSON or YAML file into a list of Rule objects."""
    path = Path(rules_path)
    if not path.exists():
        raise click.ClickException(f"Rules file not found: {path}")
    ext = path.suffix.lower()
    if ext == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    elif ext in (".yaml", ".yml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raise click.ClickException(f"Unsupported rules format '{ext}'. Expected .json or .yaml/.yml.")
    return [Rule(**item) for item in raw]


def _load_rules_from_mcp(policy_name: str, server_script: str) -> list[Rule]:
    """Fetch rules from the MCP server for the given policy name."""
    from policy_dq.mcp.client import fetch_rules
    return fetch_rules(policy_name, server_script)


def _print_summary(result: object, threshold: int) -> None:
    """Print console summary and exit non-zero if issues exceed threshold."""
    from policy_dq.models import ValidationResult
    assert isinstance(result, ValidationResult)
    total = result.metadata.get("total_issues", len(result.issues))
    if result.is_valid or total <= threshold:
        click.secho(f"✅ Validation passed — {total} issue(s) found (threshold: {threshold}).", fg="green")
    else:
        click.secho(f"❌ Validation failed — {total} issue(s) found (threshold: {threshold}).", fg="red")
        for issue in result.issues:
            row = f"row {issue.row_index}" if issue.row_index is not None else "column-level"
            click.echo(f"  [{issue.rule_type}] {issue.field_name} ({row}): {issue.message}")
        raise SystemExit(1)


@click.group()
def cli() -> None:
    """policy-dq — Policy-Driven Data Quality Validator."""


@cli.command()
@click.argument("input_file")
@click.option("--rules", default=None, help="Path to a local rules file (.json or .yaml).")
@click.option("--mcp", "policy_name", default=None, metavar="POLICY",
              help="Fetch rules from MCP server for this policy name.")
@click.option("--mcp-server", default="src/policy_dq/mcp/server.py", show_default=True,
              help="Path to the MCP server script.")
@click.option("--output-dir", default=None, help="Directory to save JSON and Markdown reports.")
@click.option("--threshold", default=0, show_default=True, type=int,
              help="Max issues allowed before exiting non-zero.")
def validate(
    input_file: str,
    rules: str | None,
    policy_name: str | None,
    mcp_server: str,
    output_dir: str | None,
    threshold: int,
) -> None:
    """Validate INPUT_FILE against a set of rules."""
    if policy_name:
        click.echo(f"Fetching rules for policy '{policy_name}' via MCP...")
        try:
            rule_list = _load_rules_from_mcp(policy_name, mcp_server)
        except Exception as exc:
            raise click.ClickException(f"MCP error: {exc}")
    elif rules:
        rule_list = _load_rules_from_file(rules)
    else:
        raise click.ClickException("Provide either --rules <file> or --mcp <policy_name>.")

    try:
        df = load_data(input_file)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc))

    result = ValidationEngine(df, rule_list).run()
    reporter = ReportGenerator(result)

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        reporter.to_json(out / "report.json")
        reporter.to_markdown(out / "report.md")
        click.echo(f"Reports saved to {out}/")

    _print_summary(result, threshold)


@cli.command()
@click.argument("report_json")
def summarize(report_json: str) -> None:
    """Print a human-readable summary of an existing REPORT_JSON file."""
    path = Path(report_json)
    if not path.exists():
        raise click.ClickException(f"Report file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON: {exc}")

    is_valid = data.get("is_valid", False)
    issues = data.get("issues", [])
    meta = data.get("metadata", {})

    click.echo(f"\nValidation Report — {'✅ PASSED' if is_valid else '❌ FAILED'}")
    click.echo(f"  Total rules : {meta.get('total_rules', '?')}")
    click.echo(f"  Total issues: {meta.get('total_issues', len(issues))}\n")

    if issues:
        click.echo(f"{'Row':<6} {'Field':<20} {'Rule':<15} Message")
        click.echo("-" * 80)
        for issue in issues:
            row = str(issue.get("row_index", "—"))
            click.echo(f"{row:<6} {issue['field_name']:<20} {issue['rule_type']:<15} {issue['message']}")


if __name__ == "__main__":
    cli()
