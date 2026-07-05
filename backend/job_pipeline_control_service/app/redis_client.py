"""Thin Redis wrapper for the kill-flag DB index (architecture.md section 7).

Only used by routes/admin.py's revoke-queued-tasks path; the kill.set MCP
tool (mcp_gateway/app/tools/kill_tools.py) is the actual source of truth
for setting kill flags — this module exists for the Celery
control.revoke() call that's specific to this service.
"""

import redis

from .config import settings


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        db=settings.redis_db_kill_flags,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
