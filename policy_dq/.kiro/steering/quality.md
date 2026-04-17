# Quality Standards

## Validation Logic
- Every validator must handle null/NaN values explicitly — skip them unless the rule is `required`
- Issues must be returned in deterministic order: sorted by `row_index` (nulls last), then `field_name`
- Validators must never raise unhandled exceptions for bad data — only for misconfigured rules

## Error Handling
- File not found → `FileNotFoundError` with a clear path in the message
- Unsupported format → `ValueError` with the offending extension named
- Unknown rule_type → `ValueError` listing available types
- CLI wraps all exceptions in `click.ClickException` — no raw tracebacks to the user

## Severity & Exit Codes
- CLI exits `0` on success, `1` when `total_issues > threshold` (default threshold: `0`)
- `--threshold N` allows pipelines to tolerate up to N issues before failing
- The `summarize` command always exits `0` — it is read-only

## Determinism
- Report output must be byte-for-byte identical for the same input
- Issue ordering: sort by `(row_index or float('inf'), field_name)` before returning from engine
- JSON reports use `indent=2` and `sort_keys=False` (insertion order is deterministic via Pydantic)

## Code Style
- No business logic in CLI or API handlers
- No bare `except:` clauses — always catch specific exception types
- All public functions and classes must have a one-line docstring minimum
