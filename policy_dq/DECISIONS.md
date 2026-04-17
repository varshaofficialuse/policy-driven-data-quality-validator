# Architectural Decisions

## 1. `uv` for dependency management

`uv` was chosen over `pip + venv` or `poetry` for its speed — dependency resolution and
environment creation are an order of magnitude faster due to its Rust-based resolver. It
also unifies lockfile management (`uv.lock`), virtual environment creation, and script
running (`uv run`) into a single tool with no separate install step. For a project cloned
and iterated on frequently, this reduces friction significantly.

Tradeoff: `uv` is newer than `poetry` and less familiar to some teams. The lockfile format
is not interchangeable with `pip-tools`. Accepted because the speed benefit is material and
the format is stable.

---

## 2. Strategy Pattern — the validator registry

Each validator is an independent class implementing a single `validate()` method. The engine
never imports validators directly — it looks them up by `rule_type` string in `RULE_REGISTRY`
defined in `src/policy_dq/rules/registry.py`:

```python
RULE_REGISTRY = {
    "required":   RequiredField,
    "type_check": TypeCheck,
    "regex":      RegexCheck,
    "range":      RangeCheck,
    "unique":     UniquenessCheck,
}
```

Adding a new rule type requires exactly two things: a new class in
`src/policy_dq/rules/validators.py` and one line in the registry. The engine, CLI, API,
and MCP server all gain it automatically. Cross-field rules use a separate
`CROSS_FIELD_REGISTRY` so the engine can pass the full DataFrame to them without
special-casing in the dispatch loop.

Tradeoff: a plugin-style approach (entry points, importlib discovery) would allow third-party
validators without modifying the package. Deferred — not warranted at this scale.

---

## 3. FastMCP for agentic rule retrieval

`FastMCP` mirrors FastAPI's decorator ergonomics — a single `@mcp.tool()` is all that's
needed to expose a Python function as an MCP tool. More importantly, it positions rule
retrieval as an agentic operation: rules are live, queryable knowledge rather than static
config files. The server (`src/policy_dq/mcp/server.py`) can be extended to fetch rules
from a database or policy engine without changing the client or engine.

The policy registry lives in `src/policy_dq/mcp/policies.py` and is shared between the
MCP server and the FastAPI endpoint, so both surfaces always serve the same rules.

Tradeoff: stdio transport spawns a subprocess per CLI invocation. For a shared deployment,
an HTTP-based MCP server would be more appropriate. Accepted for local development simplicity.

---

## 4. In-memory Pandas vs. streaming

Loading the full file into a DataFrame is fast and enables vectorised operations
(`series.duplicated()`) and cross-field access. The tradeoff is memory: a 1 GB CSV will
consume ~3–5 GB of RAM. For very large files, chunked reading (`pd.read_csv(chunksize=N)`)
with stateful accumulators, or a switch to Polars/DuckDB, would be the migration path.
The `BaseValidator` interface is compatible with that migration — only the engine's dispatch
loop would change.

---

## 5. Deterministic output ordering

Issues are sorted by `(row_index, field_name)` before being returned from the engine. This
ensures that the same input always produces byte-for-byte identical reports, which matters
for snapshot testing, diffing reports in CI, and reproducible debugging. The cost is a
single sort per validation run — negligible.

---

## 6. src/ layout

The package lives under `src/policy_dq/` rather than a flat `policy_dq/` root. This
prevents accidental imports of the local directory instead of the installed package during
testing, which is a common source of subtle bugs. `pyproject.toml` declares
`[tool.setuptools.packages.find] where = ["src"]` to wire this up correctly.

---

## Scope Choices / Intentionally Deferred

- **Property-based tests**: would strengthen edge-case coverage but add `hypothesis` as a
  dependency. Deferred in favour of deterministic example-based tests.
- **Config-driven severity thresholds per rule**: currently threshold is a single integer
  applied globally. Per-rule severity levels (warn/error/critical) would require a schema
  change to `Rule` and more complex CLI output. Deferred.
- **Plugin-style validator architecture**: the registry is explicit and auditable. Entry-point
  discovery adds complexity not warranted here.
- **Authentication on the FastAPI endpoint**: out of scope for a local validation tool.
