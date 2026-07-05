"""Re-exports agents.common.mcp_client's MCPClient so backend services and
agents share one canonical implementation (per the plan's "Shared mcp_client
note"). The implementation lives in agents/common/mcp_client.py; this
module exists so backend/* services can `from shared.mcp_client import
get_mcp_client` without depending on the agents package's internal layout.
"""

from agents.common.mcp_client import MCPClient, get_mcp_client

__all__ = ["MCPClient", "get_mcp_client"]
