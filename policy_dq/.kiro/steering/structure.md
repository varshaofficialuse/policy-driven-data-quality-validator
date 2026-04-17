# Project Structure

## Folder Layout

```
policy_dq/
  core/models.py          — Pydantic models only; no business logic
  loader/factory.py       — File loading; returns pd.DataFrame
  validator/
    base.py               — BaseValidator ABC
    rules.py              — All concrete validators + registries
    engine.py             — ValidationEngine orchestrator
  report/generator.py     — ReportGenerator (JSON + Markdown)
  mcp_server.py           — FastMCP server (run as subprocess)
  mcp_client/client.py    — MCP client; fetch_rules() sync wrapper
  cli/main.py             — Click CLI; thin adapter only
  api/
    app.py                — FastAPI app instance
    routes.py             — Route handlers; thin adapter only

tests/
  unit/                   — Tests for individual classes/functions in isolation
  integration/            — Tests for full pipeline, CLI, and report output

sample_data/
  valid.csv               — Clean dataset that passes all sample rules
  invalid.csv             — Dataset with deliberate violations
  valid.json              — JSON equivalent of valid dataset

sample_rules/
  onboarding.yaml         — Local YAML rules file (onboarding policy)
  financial.json          — Local JSON rules file (financial policy)
  mcp_example.md          — Documents the MCP-backed rule source
```

## Module Boundaries
- `core/` is imported by everyone; it imports nothing from the project
- `cli/` and `api/` are adapters — zero business logic inside them
- `validator/` has no knowledge of file formats or CLI flags
- `report/` depends only on `core/models.py`

## Naming Rules
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants/registries: `UPPER_SNAKE_CASE`
- Test files: `test_<module>.py`
- Test classes: `Test<Subject>` (no `Test` suffix on methods)

## Test Layout Expectations
- `tests/unit/` — one file per module being tested, pure unit tests, no I/O
- `tests/integration/` — full pipeline tests, CLI runner tests, tmp_path fixtures
- Every test must be deterministic — no random data, no time-dependent assertions
- Fixtures for sample data defined in `conftest.py` or inline in the test file
