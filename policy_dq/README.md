# policy-dq — Policy-Driven Data Quality Validator

Validate CSV/JSON data against configurable business rules. Rules can be defined locally
(YAML/JSON) or fetched live from an MCP server by policy name.

---

## Project Overview

policy-dq is a modular Python tool for data engineers and analysts who need to enforce
data contracts on incoming datasets — as a pre-ingestion gate in a pipeline or as a
standalone audit tool. It supports six rule types, generates JSON and Markdown reports,
and exits non-zero on failure so it works cleanly in CI.

---

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# From the policy_dq/ directory — install dependencies and the package itself
uv sync --all-groups
uv pip install -e .
```

`uv sync` installs all declared dependencies. `uv pip install -e .` installs the local
package in editable mode, which registers the `policy-dq` CLI entry point.
Activate the venv or prefix commands with `uv run`.

```bash
# Option A — activate once per session
source .venv/bin/activate
policy-dq --help

# Option B — no activation needed
uv run policy-dq --help
```

---

## Running the CLI

All examples below assume you are inside the `policy_dq/` directory.
Prefix with `uv run` if the venv is not activated.

### Validate with a local rules file

```bash
uv run policy-dq validate sample_data/valid.csv --rules sample_rules/onboarding.yaml

uv run policy-dq validate sample_data/invalid.csv \
  --rules sample_rules/onboarding.yaml \
  --output-dir ./reports
```

### Validate with MCP-fetched rules

```bash
uv run policy-dq validate sample_data/valid.csv --mcp onboarding

uv run policy-dq validate sample_data/invalid.csv \
  --mcp financial \
  --output-dir ./reports
```

Built-in policy names: `onboarding`, `financial`.

### Summarize an existing report

```bash
uv run policy-dq summarize reports/report.json
```

### All flags for `validate`

| Flag | Description |
|------|-------------|
| `INPUT_FILE` | Path to `.csv` or `.json` data file (positional, required) |
| `--rules` | Path to local `.json` or `.yaml` rules file |
| `--mcp POLICY` | Fetch rules from MCP server for this policy name |
| `--mcp-server` | Path to MCP server script (default: `src/policy_dq/mcp/server.py`) |
| `--output-dir` | Directory to save `report.json` and `report.md` |
| `--threshold N` | Max issues allowed before exiting non-zero (default: `0`) |

---

## Running Tests

```bash
uv run pytest tests/ -v
```

Unit tests only:
```bash
uv run pytest tests/unit/ -v
```

Integration tests only:
```bash
uv run pytest tests/integration/ -v
```

---

## Starting the Servers

### FastAPI server

```bash
uv run python app.py
# or
uv run uvicorn app:app --reload
```

Docs at `http://localhost:8000/docs`.

### MCP server (standalone, for debugging)

```bash
uv run python src/policy_dq/mcp/server.py
```

The CLI spawns the MCP server automatically as a subprocess when `--mcp` is used —
you only need to run it manually for debugging.

---

## Configuring and Using MCP

The MCP server (`src/policy_dq/mcp/server.py`) exposes a single tool:
`get_validation_rules(policy_name)`.

```bash
# CLI — fetches rules from MCP at runtime
uv run policy-dq validate sample_data/invalid.csv --mcp onboarding

# API
curl -X POST http://localhost:8000/validate \
  -F "file=@sample_data/invalid.csv" \
  -F "policy_name=onboarding"
```

To add a new policy, edit `_POLICIES` in `src/policy_dq/mcp/policies.py`. See
`sample_rules/mcp_example.md` for full details.

---

## Example Commands

```bash
# Validate clean data locally — should pass
uv run policy-dq validate sample_data/valid.csv --rules sample_rules/onboarding.yaml

# Validate dirty data and save reports
uv run policy-dq validate sample_data/invalid.csv \
  --rules sample_rules/onboarding.yaml \
  --output-dir ./reports

# Validate using the financial rules file
uv run policy-dq validate sample_data/valid.json \
  --rules sample_rules/financial.json

# Use MCP rules with a threshold (tolerate up to 2 issues)
uv run policy-dq validate sample_data/invalid.csv --mcp onboarding --threshold 2

# Summarize a saved report
uv run policy-dq summarize reports/report.json

# Run all tests
uv run pytest tests/ -v

# Lint the codebase
uv run ruff check src/
```

---

## Assumptions and Limitations

- **In-memory processing**: the full file is loaded into a Pandas DataFrame. Files larger
  than available RAM will fail. Chunked processing is the migration path.
- **Stdio MCP transport**: the MCP server is spawned as a subprocess per CLI invocation.
  For shared team deployments, an HTTP-based MCP server would be more appropriate.
- **No authentication**: the FastAPI endpoint has no auth. Add a middleware layer before
  exposing it publicly.
- **Date parsing**: `cross_field` with `parse_dates: true` expects ISO 8601 strings
  (`YYYY-MM-DD`). Other date formats will produce a parse error issue rather than a crash.
- **Rule ordering**: issues are sorted by `(row_index, field_name)` for determinism, not
  by rule definition order.
