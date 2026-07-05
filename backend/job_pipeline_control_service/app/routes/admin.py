"""POST /admin/kill — the real kill-switch endpoint (architecture.md section 7).

Sets Redis + CouchDB flags via the MCP gateway's kill.set tool
(mcp_gateway/app/tools/kill_tools.py implements the actual flag-setting and
audit logging). A scope="all" request additionally revokes all
queued-but-not-yet-started Celery tasks via celery.control.revoke, so
nothing new starts even before a task's own kill_switch.check() would
catch it.
"""

from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from agents.common.mcp_client import get_mcp_client
from orchestrator.celery_app import app as celery_app

router = APIRouter(prefix="/admin")


class KillRequest(BaseModel):
    scope: Literal["all", "project", "job_run"]
    scope_id: str | None = None


def _require_admin_token(x_admin_token: str | None) -> None:
    import os

    expected = os.environ.get("KILL_SWITCH_ADMIN_TOKEN")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=403, detail="admin token required for kill-switch operations")


@router.post("/kill")
def kill(request: KillRequest, x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin_token(x_admin_token)

    if request.scope != "all" and not request.scope_id:
        raise HTTPException(status_code=400, detail="scope_id is required unless scope='all'")

    mcp = get_mcp_client()
    result = mcp.kill_set(scope=request.scope, scope_id=request.scope_id, requested_by="user:admin")

    if request.scope == "all":
        celery_app.control.purge()

    return result
