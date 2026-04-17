import asyncio
import sys
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from policy_dq.models import Rule


async def _fetch_rules_async(policy_name: str, server_script: str) -> list[Rule]:
    """Connect to the MCP server via stdio and call get_validation_rules."""
    server_params = StdioServerParameters(command=sys.executable, args=[server_script])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_validation_rules",
                arguments={"policy_name": policy_name},
            )
            import json
            raw: list[dict] = [json.loads(item.text) for item in result.content]
            return [Rule(**item) for item in raw]


def fetch_rules(policy_name: str, server_script: str = "src/policy_dq/mcp/server.py") -> list[Rule]:
    """Synchronous wrapper — runs in a dedicated thread to avoid event loop conflicts."""
    result: list[Rule] = []
    exc_holder: list[BaseException] = []

    def _run() -> None:
        try:
            result.extend(asyncio.run(_fetch_rules_async(policy_name, server_script)))
        except BaseException as e:
            exc_holder.append(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join()

    if exc_holder:
        raise exc_holder[0]
    return result
