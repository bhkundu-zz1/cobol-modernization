"""Client for the MCP gateway — the ONLY way agent code reaches CouchDB,
the audit log, kill-switch state, or the mainframe connector (architecture.md
section 1).

No agent module in this repo should import ibmcloudant, a redis client, or
an httpx client pointed at any other service directly — everything routes
through this module.

The MCP gateway speaks the real MCP protocol (JSON-RPC over HTTP/SSE via
FastMCP), not plain REST — confirmed against a live FastMCP 3.4.2 server.
`fastmcp.Client` is the correct client for that protocol; this module wraps
it with a synchronous interface, since callers span both genuinely sync
contexts (Celery task bodies) and async contexts (FastAPI route handlers,
which already run inside a live event loop — `asyncio.run()` raises
RuntimeError there, confirmed as a live bug the first time a FastAPI
service called this client). `_call_tool` detects which situation it's in:
outside a running loop it uses `asyncio.run()` directly; inside one, it
runs the coroutine on a dedicated background thread with its own loop so
FastAPI's request-handling loop is never blocked or nested.
"""

import asyncio
import os
import threading
from typing import Any

from fastmcp import Client as FastMCPClient


def _run_coroutine_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop running in this thread — the common case for Celery tasks.
        return asyncio.run(coro)

    # Already inside a running loop (e.g. a FastAPI async route handler) —
    # run the coroutine to completion on a separate thread with its own loop.
    result: dict[str, Any] = {}
    error: list[BaseException] = []

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - re-raised on the calling thread below
            error.append(exc)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result["value"]


class MCPClient:
    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        base = (base_url or os.environ.get("MCP_GATEWAY_URL", "http://localhost:7000")).rstrip("/")
        self._mcp_url = base if base.endswith("/mcp") else f"{base}/mcp"
        self._timeout = timeout

    def _call_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        async def _call() -> dict[str, Any]:
            async with FastMCPClient(self._mcp_url, timeout=self._timeout) as client:
                result = await client.call_tool(tool_name, kwargs)
                return result.data

        return _run_coroutine_sync(_call())

    # --- couchdb ---------------------------------------------------------------

    def couchdb_read(
        self,
        database: str,
        doc_id: str | None = None,
        mango_selector: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        return self._call_tool(
            "couchdb_read", database=database, doc_id=doc_id, mango_selector=mango_selector, limit=limit
        )

    def couchdb_write(self, database: str, doc: dict[str, Any], project_id: str, created_by: str, trace_id: str) -> dict[str, Any]:
        return self._call_tool(
            "couchdb_write", database=database, doc=doc, project_id=project_id, created_by=created_by, trace_id=trace_id
        )

    # --- audit -------------------------------------------------------------------

    def audit_append(
        self,
        project_id: str,
        event_category: str,
        actor: dict[str, str],
        action: str,
        subject_doc_id: str,
        subject_doc_rev: str | None = None,
        before_state_hash: str | None = None,
        after_state_hash: str | None = None,
        model_used: str | None = None,
        skill_version_hash: str | None = None,
    ) -> dict[str, Any]:
        return self._call_tool(
            "audit_append",
            project_id=project_id,
            event_category=event_category,
            actor=actor,
            action=action,
            subject_doc_id=subject_doc_id,
            subject_doc_rev=subject_doc_rev,
            before_state_hash=before_state_hash,
            after_state_hash=after_state_hash,
            model_used=model_used,
            skill_version_hash=skill_version_hash,
        )

    # --- kill-switch ---------------------------------------------------------------

    def kill_check(self, project_id: str, job_run_id: str) -> dict[str, Any]:
        return self._call_tool("kill_check", project_id=project_id, job_run_id=job_run_id)

    def kill_set(self, scope: str, requested_by: str, scope_id: str | None = None) -> dict[str, Any]:
        return self._call_tool("kill_set", scope=scope, scope_id=scope_id, requested_by=requested_by)

    # --- mainframe -------------------------------------------------------------------

    def mainframe_fetch_source(
        self,
        tool: str,
        host: str,
        credential_ref: str,
        system: str,
        subsystem: str,
        element_type: str,
        requesting_agent: str,
        project_id: str,
        element_id: str | None = None,
    ) -> dict[str, Any]:
        return self._call_tool(
            "mainframe_fetch_source",
            tool=tool,
            host=host,
            credential_ref=credential_ref,
            system=system,
            subsystem=subsystem,
            element_type=element_type,
            requesting_agent=requesting_agent,
            project_id=project_id,
            element_id=element_id,
        )

    # --- issue tracker export -------------------------------------------------------------------

    def issue_tracker_export(
        self,
        tool: str,
        connection_config: dict[str, Any],
        epic_ids: list[str],
        story_ids: list[str],
        requesting_agent: str,
        project_id: str,
    ) -> dict[str, Any]:
        return self._call_tool(
            "issue_tracker_export",
            tool=tool,
            connection_config=connection_config,
            epic_ids=epic_ids,
            story_ids=story_ids,
            requesting_agent=requesting_agent,
            project_id=project_id,
        )


_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient()
    return _client
