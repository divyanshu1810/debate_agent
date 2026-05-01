"""
Thin async context-manager wrapper around FastMCP's HTTP client.

Usage:
    async with MCPClient("http://localhost:8001/mcp") as mcp:
        results = await mcp.call_tool("search_tool", {"query": "..."})
"""

from fastmcp import Client as _FastMCPClient
import json


class MCPClient:
    """Async context-manager that wraps a FastMCP HTTP client."""

    def __init__(self, url: str):
        self.url = url
        self._client: _FastMCPClient | None = None

    async def __aenter__(self) -> "MCPClient":
        self._client = _FastMCPClient(self.url)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def call_tool(self, name: str, arguments: dict):
        """
        Call an MCP tool and return the parsed result.

        FastMCP's client.call_tool() returns a CallToolResult object with:
          - .content  — list of TextContent / ImageContent / … blocks
          - .isError  — bool indicating a tool-level error

        We extract the first text block and JSON-decode it transparently so
        callers always receive plain Python objects.
        """
        if self._client is None:
            raise RuntimeError("MCPClient must be used as an async context manager")

        result = await self._client.call_tool(name, arguments)

        # result is a CallToolResult — pull the content list out of it.
        # Older fastmcp versions returned the list directly; support both.
        if hasattr(result, "content"):
            content_blocks = result.content
            if getattr(result, "isError", False):
                raise RuntimeError(f"MCP tool '{name}' returned an error: {content_blocks}")
        elif hasattr(result, "__iter__"):
            # Legacy fastmcp that returned a bare list
            content_blocks = list(result)
        else:
            content_blocks = [result]

        if not content_blocks:
            return []

        # Extract text from the first content block.
        raw = content_blocks[0].text if hasattr(content_blocks[0], "text") else str(content_blocks[0])

        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
