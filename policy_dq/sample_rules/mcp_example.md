# MCP-Backed Rule Source

Rules can be fetched at runtime from the built-in MCP server instead of a local file.

## Available Policies

| Policy name  | Description                              |
|--------------|------------------------------------------|
| `onboarding` | Validates new user registration records  |
| `financial`  | Validates financial transaction records  |

## How to Use

### Via CLI
```bash
# Start validation using MCP-fetched rules
policy-dq validate sample_data/valid.csv --mcp onboarding
policy-dq validate sample_data/invalid.csv --mcp financial --output-dir ./reports
```

### Via API
```bash
curl -X POST http://localhost:8000/validate \
  -F "file=@sample_data/invalid.csv" \
  -F "policy_name=onboarding"
```

## How It Works

1. The CLI/API calls `fetch_rules(policy_name)` in `policy_dq/mcp_client/client.py`
2. The client spawns `policy_dq/mcp_server.py` as a subprocess via stdio transport
3. It calls the `get_validation_rules` MCP tool with the policy name
4. The server returns a JSON list of rule dicts
5. These are parsed into `list[Rule]` and passed to `ValidationEngine` — identical to local rules

## Adding a New Policy

Edit `_POLICIES` in `policy_dq/mcp_server.py`:

```python
_POLICIES["my_policy"] = [
    {"field_name": "id", "rule_type": "required", "params": {}},
    {"field_name": "id", "rule_type": "unique",   "params": {}},
]
```
