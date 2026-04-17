# Tech Stack

## Python Version
Python 3.12+ (declared in `.python-version` and `pyproject.toml`)

## Package & Tooling
- `uv` for dependency management, virtual environments, and script running
- `pyproject.toml` as the single project config file (no setup.py, no requirements.txt)
- Entry point wired via `[project.scripts]`: `policy-dq = "policy_dq.cli.main:cli"`

## Core Libraries
- `pydantic>=2` — all data models; use `model_dump()` not `.dict()`
- `pandas>=2` — DataFrame loading and column-level validation
- `click` — CLI framework
- `fastapi` + `uvicorn` — HTTP API layer
- `mcp` (FastMCP) — MCP server and client
- `pyyaml` — YAML rules file parsing

## Linting & Formatting
- `ruff` — linting and formatting (replaces flake8 + black + isort)
- Run: `uv run ruff check .` and `uv run ruff format .`

## Testing
- `pytest` — test runner
- `pytest-asyncio` — async test support
- Run all tests: `uv run pytest tests/ -v`

## Typing Expectations
- Full type hints on all function signatures and return types
- No use of `Any` unless genuinely unavoidable (e.g. `dict[str, Any]` for open params)
- Use `X | Y` union syntax (Python 3.10+), not `Optional[X]` or `Union[X, Y]`
