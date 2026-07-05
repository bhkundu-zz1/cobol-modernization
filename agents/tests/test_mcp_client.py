"""Regression test: MCPClient must work from both a sync context (Celery
tasks) and from inside an already-running asyncio event loop (FastAPI async
route handlers) — a live bug the first time a FastAPI service called
get_mcp_client() (asyncio.run() raised "cannot be called from a running
event loop"). No real MCP gateway is reachable in this unit test; only the
event-loop-nesting behavior of _run_coroutine_sync is under test.
"""

import asyncio

import pytest

from agents.common.mcp_client import _run_coroutine_sync


async def _return_42() -> int:
    return 42


async def _raise_value_error() -> None:
    raise ValueError("boom")


def test_run_coroutine_sync_outside_a_running_loop():
    assert _run_coroutine_sync(_return_42()) == 42


def test_run_coroutine_sync_propagates_exceptions_outside_a_loop():
    with pytest.raises(ValueError, match="boom"):
        _run_coroutine_sync(_raise_value_error())


def test_run_coroutine_sync_from_inside_a_running_loop():
    """Simulates calling _call_tool from within a FastAPI async route
    handler, where asyncio.get_running_loop() succeeds and a bare
    asyncio.run() would raise RuntimeError."""

    async def caller() -> int:
        return _run_coroutine_sync(_return_42())

    assert asyncio.run(caller()) == 42


def test_run_coroutine_sync_propagates_exceptions_from_inside_a_running_loop():
    async def caller() -> None:
        _run_coroutine_sync(_raise_value_error())

    with pytest.raises(ValueError, match="boom"):
        asyncio.run(caller())
