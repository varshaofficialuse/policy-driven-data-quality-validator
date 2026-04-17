"""Shared policy registry — used by MCP server and API route."""
from policy_dq.models import Rule

_POLICIES: dict[str, list[dict]] = {
    "onboarding": [
        {"field_name": "email",     "rule_type": "required", "params": {}},
        {"field_name": "email",     "rule_type": "regex",    "params": {"pattern": r"[^@]+@[^@]+\.[^@]+"}},
        {"field_name": "age",       "rule_type": "range",    "params": {"min": 18, "max": 120}},
        {"field_name": "full_name", "rule_type": "required", "params": {}},
        {"field_name": "user_id",   "rule_type": "unique",   "params": {}},
    ],
    "financial": [
        {"field_name": "account_id", "rule_type": "required",   "params": {}},
        {"field_name": "account_id", "rule_type": "unique",     "params": {}},
        {"field_name": "amount",     "rule_type": "type_check", "params": {"expected_type": "float"}},
        {"field_name": "amount",     "rule_type": "range",      "params": {"min": 0}},
        {"field_name": "currency",   "rule_type": "regex",      "params": {"pattern": r"[A-Z]{3}"}},
        {"field_name": "end_date",   "rule_type": "cross_field",
         "params": {"compare_field": "start_date", "operator": "gt", "parse_dates": True}},
    ],
}


def get_rules_for_policy(policy_name: str) -> list[Rule]:
    """Return Rule objects for a named policy.

    Raises:
        ValueError: if policy_name is not recognised.
    """
    raw = _POLICIES.get(policy_name.lower())
    if raw is None:
        raise ValueError(f"Unknown policy '{policy_name}'. Available: {list(_POLICIES)}")
    return [Rule(**item) for item in raw]
