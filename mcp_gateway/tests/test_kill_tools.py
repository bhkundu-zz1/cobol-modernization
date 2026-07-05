from app.schemas import KillCheckRequest, KillSetRequest
from app.tools.kill_tools import GLOBAL_KEY, _job_key, _project_key, kill_check, kill_set


def test_kill_check_false_when_no_flags_set(fake_redis, fake_couchdb):
    result = kill_check(fake_redis, fake_couchdb, KillCheckRequest(project_id="acme-2026", job_run_id="jr-1"))
    assert result.killed is False


def test_kill_check_true_when_global_flag_set(fake_redis, fake_couchdb):
    fake_redis.set(GLOBAL_KEY, "1")
    result = kill_check(fake_redis, fake_couchdb, KillCheckRequest(project_id="acme-2026", job_run_id="jr-1"))
    assert result.killed is True
    assert "global" in result.reason


def test_kill_check_true_when_project_flag_set(fake_redis, fake_couchdb):
    fake_redis.set(_project_key("acme-2026"), "1")
    result = kill_check(fake_redis, fake_couchdb, KillCheckRequest(project_id="acme-2026", job_run_id="jr-1"))
    assert result.killed is True


def test_kill_check_true_when_job_flag_set(fake_redis, fake_couchdb):
    fake_redis.set(_job_key("jr-1"), "1")
    result = kill_check(fake_redis, fake_couchdb, KillCheckRequest(project_id="acme-2026", job_run_id="jr-1"))
    assert result.killed is True


def test_kill_check_falls_back_to_couchdb_when_redis_unreachable(fake_couchdb):
    class BrokenRedis:
        def get(self, key):
            import redis

            raise redis.RedisError("connection refused")

    fake_couchdb.put_document(
        "agent_runs",
        {
            "_id": "acme-2026:jr-1:job_run",
            "type": "job_run",
            "job_run_id": "jr-1",
            "project_id": "acme-2026",
            "kill_requested": True,
        },
    )

    result = kill_check(BrokenRedis(), fake_couchdb, KillCheckRequest(project_id="acme-2026", job_run_id="jr-1"))
    assert result.killed is True
    assert "couchdb fallback" in result.reason


def test_kill_check_fails_safe_when_both_unreachable(fake_couchdb):
    class BrokenRedis:
        def get(self, key):
            import redis

            raise redis.RedisError("connection refused")

    # No job_run doc exists in CouchDB either -> state is genuinely unknown.
    result = kill_check(BrokenRedis(), fake_couchdb, KillCheckRequest(project_id="acme-2026", job_run_id="jr-missing"))
    assert result.killed is True, "uncertain kill-switch state must fail safe to killed=True"


def test_kill_set_job_run_scope_sets_redis_and_couchdb_and_audits(fake_redis, fake_couchdb):
    fake_couchdb.put_document(
        "agent_runs",
        {
            "_id": "acme-2026:jr-1:job_run",
            "type": "job_run",
            "job_run_id": "jr-1",
            "project_id": "acme-2026",
            "kill_requested": False,
        },
    )

    result = kill_set(
        fake_redis,
        fake_couchdb,
        KillSetRequest(scope="job_run", scope_id="jr-1", requested_by="user:bhakti.kundu@gmail.com"),
    )
    assert result.ok is True
    assert fake_redis.get(_job_key("jr-1")) == "1"

    job_run = fake_couchdb.find("agent_runs", {"job_run_id": "jr-1"})["docs"][0]
    assert job_run["kill_requested"] is True
    assert job_run["kill_requested_by"] == "user:bhakti.kundu@gmail.com"

    audit_events = fake_couchdb.find("audit_log", {"type": "audit_event", "event_category": "kill_switch"})["docs"]
    assert len(audit_events) == 1


def test_kill_set_global_scope_sets_global_flag(fake_redis, fake_couchdb):
    kill_set(fake_redis, fake_couchdb, KillSetRequest(scope="all", requested_by="user:admin@example.com"))
    assert fake_redis.get(GLOBAL_KEY) == "1"
