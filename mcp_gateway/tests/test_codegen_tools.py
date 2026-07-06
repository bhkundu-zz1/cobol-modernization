"""Exercises codegen.commit_files against a mocked GitHub REST/Git Data
API (httpx.MockTransport — respx confirmed unavailable in this
environment, same as agents/tests/test_issue_tracker_adapter.py), covering
the blob->tree->commit->ref-update sequence, path-traversal defenses, and
the concurrent-ref-move retry.
"""

import httpx
import pytest

from app.config import settings
from app.schemas import CodegenFileEntry, CodegenCommitFilesRequest
from app.tools.codegen_tools import CodegenCommitRejected, codegen_commit_files

OWNER = "acme-org"
REPO = "generated-migrations"
BRANCH = "main"


@pytest.fixture(autouse=True)
def _git_config_and_token(monkeypatch):
    monkeypatch.setattr(settings, "codegen_git_repo_owner", OWNER)
    monkeypatch.setattr(settings, "codegen_git_repo_name", REPO)
    monkeypatch.setattr(settings, "codegen_git_branch", BRANCH)
    monkeypatch.setenv("CODEGEN_GIT_TOKEN", "ghp_faketoken")


def _patched_client(monkeypatch, transport: httpx.MockTransport) -> None:
    real_client = httpx.Client

    def factory(**kwargs):
        kwargs["transport"] = transport
        return real_client(**kwargs)

    monkeypatch.setattr("app.tools.codegen_tools.httpx.Client", factory)


def _happy_path_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}":
        return httpx.Response(200, json={"object": {"sha": "branch-tip-sha"}})
    if path == "/repos/{}/{}/git/commits/branch-tip-sha".format(OWNER, REPO):
        return httpx.Response(200, json={"tree": {"sha": "base-tree-sha"}})
    if path == f"/repos/{OWNER}/{REPO}/git/blobs":
        return httpx.Response(201, json={"sha": f"blob-sha-{request.content[:8].hex()}"})
    if path == f"/repos/{OWNER}/{REPO}/git/trees":
        return httpx.Response(201, json={"sha": "new-tree-sha"})
    if path == f"/repos/{OWNER}/{REPO}/git/commits":
        return httpx.Response(201, json={"sha": "new-commit-sha"})
    if path == f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}":
        return httpx.Response(200, json={"object": {"sha": "new-commit-sha"}})
    raise AssertionError(f"unexpected path: {path}")


def _request(files: list[CodegenFileEntry], story_id: str = "story-a") -> CodegenCommitFilesRequest:
    return CodegenCommitFilesRequest(
        project_id="acme-2026",
        story_id=story_id,
        files=files,
        commit_message="Generate python microservice for story story-a",
        requesting_agent="codegen-python@v1",
    )


def test_happy_path_commits_all_files_in_one_commit(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request(
        [
            CodegenFileEntry(relative_path="app/main.py", content="print('hi')"),
            CodegenFileEntry(relative_path="requirements.txt", content="fastapi"),
        ]
    )

    result = codegen_commit_files(fake_couchdb, request)

    assert result.commit_sha == "new-commit-sha"
    assert result.commit_url == f"https://github.com/{OWNER}/{REPO}/commit/new-commit-sha"
    assert result.repo_path == "story-a"


def test_tree_entries_are_scoped_under_story_id_path(fake_couchdb, monkeypatch):
    captured_tree_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/repos/{OWNER}/{REPO}/git/trees":
            import json

            captured_tree_request.update(json.loads(request.content))
            return httpx.Response(201, json={"sha": "new-tree-sha"})
        return _happy_path_handler(request)

    _patched_client(monkeypatch, httpx.MockTransport(handler))
    request = _request([CodegenFileEntry(relative_path="app/main.py", content="print('hi')")], story_id="story-xyz")

    codegen_commit_files(fake_couchdb, request)

    tree_paths = [entry["path"] for entry in captured_tree_request["tree"]]
    assert tree_paths == ["story-xyz/app/main.py"]


def test_rejects_relative_path_traversal_with_dotdot(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request([CodegenFileEntry(relative_path="../escape.txt", content="x")])
    with pytest.raises(CodegenCommitRejected):
        codegen_commit_files(fake_couchdb, request)


def test_rejects_absolute_relative_path(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request([CodegenFileEntry(relative_path="/etc/passwd", content="x")])
    with pytest.raises(CodegenCommitRejected):
        codegen_commit_files(fake_couchdb, request)


def test_rejects_story_id_with_path_separator(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request([CodegenFileEntry(relative_path="x.txt", content="x")], story_id="story/../escape")
    with pytest.raises(CodegenCommitRejected):
        codegen_commit_files(fake_couchdb, request)


def test_rejects_oversized_file_count(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    files = [CodegenFileEntry(relative_path=f"f{i}.txt", content="x") for i in range(41)]
    request = _request(files)
    with pytest.raises(CodegenCommitRejected):
        codegen_commit_files(fake_couchdb, request)


def test_rejects_oversized_total_bytes(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    big_content = "x" * (2 * 1024 * 1024 + 1)
    request = _request([CodegenFileEntry(relative_path="big.txt", content=big_content)])
    with pytest.raises(CodegenCommitRejected):
        codegen_commit_files(fake_couchdb, request)


def test_rejects_when_token_not_configured(fake_couchdb, monkeypatch):
    monkeypatch.delenv("CODEGEN_GIT_TOKEN", raising=False)
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request([CodegenFileEntry(relative_path="x.txt", content="x")])
    with pytest.raises(CodegenCommitRejected, match="CODEGEN_GIT_TOKEN"):
        codegen_commit_files(fake_couchdb, request)


def test_rejects_when_repo_not_configured(fake_couchdb, monkeypatch):
    monkeypatch.setattr(settings, "codegen_git_repo_owner", "")
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request([CodegenFileEntry(relative_path="x.txt", content="x")])
    with pytest.raises(CodegenCommitRejected, match="CODEGEN_GIT_REPO"):
        codegen_commit_files(fake_couchdb, request)


def test_retries_when_branch_ref_moves_concurrently(fake_couchdb, monkeypatch):
    attempt_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}":
            attempt_count["n"] += 1
            if attempt_count["n"] == 1:
                return httpx.Response(422, json={"message": "reference update failed"})
            return httpx.Response(200, json={"object": {"sha": "new-commit-sha"}})
        return _happy_path_handler(request)

    _patched_client(monkeypatch, httpx.MockTransport(handler))
    request = _request([CodegenFileEntry(relative_path="app/main.py", content="print('hi')")])

    result = codegen_commit_files(fake_couchdb, request)

    assert attempt_count["n"] == 2
    assert result.commit_sha == "new-commit-sha"


def test_raises_after_exhausting_ref_move_retries(fake_couchdb, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}":
            return httpx.Response(422, json={"message": "reference update failed"})
        return _happy_path_handler(request)

    _patched_client(monkeypatch, httpx.MockTransport(handler))
    request = _request([CodegenFileEntry(relative_path="app/main.py", content="print('hi')")])

    with pytest.raises(CodegenCommitRejected, match="moved concurrently"):
        codegen_commit_files(fake_couchdb, request)


def test_writes_audit_event(fake_couchdb, monkeypatch):
    _patched_client(monkeypatch, httpx.MockTransport(_happy_path_handler))
    request = _request([CodegenFileEntry(relative_path="x.txt", content="x")])

    codegen_commit_files(fake_couchdb, request)

    events = fake_couchdb._dbs.get("audit_log", {})
    actions = [doc.get("action") for doc in events.values()]
    assert "codegen_commit_files" in actions
