# Feature Spec: Policy-Driven Data Quality Validator

## Requirements

### Functional
- Accept CSV and JSON input files
- Load validation rules from a local YAML/JSON file or from an MCP server by policy name
- Validate data against: required field, type check, regex, numeric range, uniqueness, cross-field
- Output a console summary, a JSON report, and a Markdown report
- CLI exits with non-zero status when issues exceed a configurable severity threshold
- Expose a Python API fully decoupled from the CLI layer

### Non-Functional
- Full type hints throughout
- Deterministic output ordering (issues ordered by row_index, then field_name)
- Clean error messages for missing files, unknown rule types, unsupported formats

---

## Design

### Architecture

```
policy_dq/
  core/models.py          — Pydantic models: Rule, ValidationIssue, ValidationResult
  loader/factory.py       — File-type detection and DataFrame loading
  validator/
    base.py               — BaseValidator ABC
    rules.py              — Concrete validators + RULE_REGISTRY + CROSS_FIELD_REGISTRY
    engine.py             — ValidationEngine: dispatches rules, collects issues
  report/generator.py     — ReportGenerator: to_json(), to_markdown()
  mcp_server.py           — FastMCP server exposing get_validation_rules(policy_name)
  mcp_client/client.py    — Async MCP client + sync fetch_rules() wrapper
  cli/main.py             — Click CLI: validate, summarize commands
  api/routes.py           — FastAPI POST /validate endpoint
```

### Validation Flow

1. CLI/API receives data file path + rules source (local file or MCP policy name)
2. `loader.factory.load_data()` detects extension, returns DataFrame
3. Rules loaded via `_load_rules_from_file()` or `fetch_rules()` → `list[Rule]`
4. `ValidationEngine(df, rules).run()` iterates rules:
   - Cross-field rules → `CROSS_FIELD_REGISTRY` → `CrossFieldCheck.validate(df)`
   - Single-column rules → `RULE_REGISTRY` → `BaseValidator.validate(series)`
5. Returns `ValidationResult` with `is_valid`, `issues`, `errors`, `metadata`
6. `ReportGenerator` writes JSON and/or Markdown
7. CLI prints console summary, exits 1 if `total_issues > threshold`

### Report Generation Flow

- `to_json(path)` — `result.model_dump()` serialised with `json.dumps(indent=2)`
- `to_markdown(path)` — status header + metadata summary + issues table

### MCP Integration Approach

- Server: `FastMCP` with a single `get_validation_rules(policy_name)` tool
- Transport: stdio (subprocess) — no network port required
- Client: `mcp.ClientSession` over `stdio_client`, result parsed from `TextContent[0].text`
- The CLI `--mcp POLICY` flag triggers client fetch; `--rules FILE` uses local loading
- Both paths produce identical `list[Rule]` fed into the same engine

### Module Boundaries

- Business logic lives exclusively in `validator/`, `loader/`, `report/`, `mcp_client/`
- `cli/main.py` and `api/routes.py` are thin adapters — no validation logic inside them
- `core/models.py` is imported by all layers; it imports nothing from the project

---

## Tasks

- [x] Define Pydantic models (Rule, ValidationIssue, ValidationResult)
- [x] Implement loader with CSV/JSON detection and error handling
- [x] Implement BaseValidator ABC
- [x] Implement RequiredField, TypeCheck, RegexCheck, RangeCheck, UniquenessCheck
- [x] Implement CrossFieldCheck with operator and parse_dates support
- [x] Implement ValidationEngine with dual registry dispatch
- [x] Implement ReportGenerator (JSON + Markdown)
- [x] Implement FastMCP server with onboarding and financial policies
- [x] Implement async MCP client with sync wrapper
- [x] Implement CLI: validate command (local + MCP rules, --output-dir, --threshold)
- [x] Implement CLI: summarize command
- [x] Implement FastAPI POST /validate endpoint
- [x] Write unit tests for all validator types
- [x] Write integration tests for full pipeline, CLI, and reports
- [x] Add sample_data/ and sample_rules/ with valid/invalid datasets
- [x] Write README, DECISIONS, KIRO_USAGE docs

---

## Design Tradeoffs

### In-memory DataFrame vs. streaming
Loading the full file into Pandas is fast and enables vectorised operations and cross-field
access. The tradeoff is memory usage for large files. Chunked reading or Polars would be the
migration path — the BaseValidator interface supports it without changes.

### Stdio MCP transport vs. HTTP
Stdio requires no running server process and no port management, which simplifies local
development and testing. The tradeoff is that it spawns a subprocess per CLI invocation.
An HTTP-based MCP server would be better for a shared team deployment.

### Single RULE_REGISTRY vs. plugin discovery
The registry dict is explicit and easy to audit. A plugin-style approach (entry points,
importlib discovery) would allow third-party validators without modifying the package, but
adds complexity not warranted at this scale.
