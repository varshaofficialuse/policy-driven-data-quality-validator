# How Kiro Was Used to Build This Project

## Spec-Driven Development

The project was built using Kiro's Spec feature. Requirements were formalised in
`.kiro/specs/feature_spec.md` before any code was written. The spec defined:

- Pydantic data models
- The four main components (Loader, Validator Engine, MCP Client, Report Generator)
- The full validation flow from file input to report output
- The MCP integration approach (stdio transport, `get_validation_rules` tool)
- Design tradeoffs (in-memory vs. streaming, registry vs. plugins)
- A task checklist used to track incremental delivery

This acted as a shared contract between the developer and the agent. Each implementation
session referenced the spec explicitly, so the agent always had the full picture rather
than responding to isolated prompts. The spec enabled incremental delivery: models first,
then validator logic, then data handling and CLI, then MCP integration, then API and tests.

---

## Steering Files

Four steering files were created in `.kiro/steering/`:

**`product.md`** — defined the target user (data engineers/analysts), primary use case
(pre-ingestion data contract enforcement), and success criteria. This kept the agent from
over-engineering features that weren't needed for the core use case.

**`tech.md`** — declared the canonical stack: `uv`, Pydantic v2, Pandas, Click, FastAPI,
FastMCP, ruff. When adding dependencies or choosing between libraries, the agent defaulted
to this list without being asked.

**`structure.md`** — described the folder layout, module boundaries (no business logic in
CLI/API), naming conventions, and test layout expectations (`tests/unit/` vs
`tests/integration/`). This prevented the agent from placing logic in the wrong layer.

**`quality.md`** — specified deterministic output ordering, null handling rules, error
handling patterns, severity threshold behaviour, and the no-bare-except rule. This was the
most impactful steering file: it directly shaped the engine's sort step and the CLI's
threshold flag, which were added proactively by the agent after reading it.

---

## Hooks

Three hooks were configured in `.kiro/hooks/`:

**`validator-lint-test`** (fileEdited on `src/policy_dq/rules/*.py` and
`src/policy_dq/validators/*.py`) — runs
`uv run ruff check src/policy_dq/rules/ src/policy_dq/validators/ && uv run pytest tests/ --tb=short -q`
on every save to the validator or rules modules. The `&&` short-circuits on lint errors so
pytest only runs on clean code. This caught a missing import and a registry key typo during
`CrossFieldCheck` development immediately on save, before the changes were committed.

**`post-task-tests`** (postTaskExecution) — runs `uv run pytest tests/ --tb=short -q`
after every spec task is marked complete. This ensured that completing one task never
silently broke a previous one.

**`remind-tests-on-create`** (fileCreated on `src/policy_dq/**/*.py`) — asks the agent to
check whether a new source file has corresponding tests in `tests/unit/` or
`tests/integration/` and suggest what cases to cover. This enforced test coverage
discipline throughout the build.

---

## MCP Integration

The MCP server (`src/policy_dq/mcp/server.py`) was built with FastMCP and exposes a single
tool: `get_validation_rules(policy_name)`. It ships two built-in policies (`onboarding`,
`financial`) defined in `src/policy_dq/mcp/policies.py`, and is designed to be extended
by editing `_POLICIES` in that file.

The client (`src/policy_dq/mcp/client.py`) connects via stdio transport, calls the tool,
and returns a typed `list[Rule]` — identical to what local file loading produces. The
engine, CLI, and API have no knowledge of where rules came from.

The CLI `--mcp POLICY` flag and the API `policy_name` form field both trigger the MCP
path. The integration test mocks `fetch_rules` to avoid spawning a subprocess in CI.

---

## Where Kiro Accelerated Development

- **Boilerplate scaffolding**: the entire package structure (`__init__.py` files,
  `pyproject.toml` wiring, entry point config) was created in a single agent turn —
  ~20–30 minutes of mechanical setup done instantly.
- **Parallel file creation**: the agent created `base.py`, `validators.py`, and `engine.py`
  in one turn, keeping the interfaces consistent across all three files.
- **Test generation**: unit and integration tests were generated with correct fixtures,
  edge cases, and assertions in one pass, covering all six validator types plus CLI
  runner tests and report output tests.
- **Documentation**: README, DECISIONS, and KIRO_USAGE were drafted in one turn with
  accurate content derived from the actual implementation.

---

## Where Kiro Output Was Corrected

- **`pyproject.toml` edit**: when adding `[project.scripts]`, the agent placed the block
  in the wrong position (inside `[project]` rather than as a separate top-level section),
  breaking the TOML structure. This was caught and corrected immediately.
- **CLI interface**: the initial `validate` command used `--data` as a flag rather than
  a positional argument, and was missing `--output-dir` and `--threshold`. The assignment
  spec required a specific interface (`policy-dq validate <file> --rules ...`), so the
  CLI was rewritten to match.
- **Test structure**: the initial tests were placed in a flat `tests/` directory. The
  assignment required `tests/unit/` and `tests/integration/` subdirectories, so the tests
  were reorganised and expanded with CLI runner tests and additional edge cases. Two stale
  root-level test files importing from old module paths were removed.
- **Steering files**: the initial `tech_stack.md` and `architecture.md` files were created
  empty. They were replaced with four properly named, content-filled steering files
  matching the assignment's requirements (`product.md`, `tech.md`, `structure.md`,
  `quality.md`).
- **Hook paths**: the `validator-lint-test` hook initially referenced the old
  `policy_dq/validator/` path. Updated to match the actual `src/policy_dq/rules/` and
  `src/policy_dq/validators/` layout, and `remind-tests-on-create` was fixed from a
  broken `runCommand` to a proper `askAgent` action.
