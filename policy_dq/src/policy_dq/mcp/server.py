from mcp.server.fastmcp import FastMCP

from policy_dq.mcp.policies import _POLICIES

mcp = FastMCP("policy-dq-rules")


@mcp.tool()
def get_validation_rules(policy_name: str) -> list[dict]:
    """Return the list of validation rules for a given policy name.

    Args:
        policy_name: Name of the policy (e.g. 'onboarding', 'financial').

    Returns:
        List of rule dicts compatible with the Rule Pydantic model.

    Raises:
        ValueError: if the policy_name is not recognised.
    """
    rules = _POLICIES.get(policy_name.lower())
    if rules is None:
        raise ValueError(f"Unknown policy '{policy_name}'. Available: {list(_POLICIES)}")
    return rules


if __name__ == "__main__":
    mcp.run()
