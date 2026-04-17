# Product

## Purpose
policy-dq is a policy-driven data quality validator. It validates structured data files
(CSV, JSON) against configurable business rules and produces human- and machine-readable reports.

## Target User
Data engineers and analysts who need to enforce data contracts on incoming datasets —
either as a pre-ingestion gate in a pipeline or as a standalone audit tool.

## Primary Use Case
A user has a CSV file of customer records. They define (or fetch via MCP) a set of rules
for their domain (e.g. "onboarding" policy). They run the CLI, get a console summary of
violations, and optionally save a JSON report for downstream systems and a Markdown report
for human review.

## Success Criteria
- All six rule types (required, type_check, regex, range, unique, cross_field) work correctly
- Both local and MCP-backed rule loading work end-to-end
- CLI exits non-zero on validation failure, enabling use in CI pipelines
- Reports are deterministic — same input always produces same output
- Tests pass with zero flakiness
