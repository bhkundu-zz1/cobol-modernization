"""codegen.commit_files — commits agent-generated files to a
client-configured GitHub repository as one commit (architecture.md section
3.2's code-generation stage).

No filesystem/shared-volume involvement: this is pure HTTP against the
GitHub REST/Git Data API, mirroring
agents/issue_tracker_export/adapter.py's GitHubAdapter, which is the only
other adapter in this repo that dereferences a real credential and makes
outbound calls. Every file is written to a single logical commit via the
blob -> tree -> commit -> ref-update sequence (not one commit per file),
under a story-scoped folder (`{story_id}/...`) in the target repo.
"""

import base64
import os
from typing import TYPE_CHECKING

import httpx

from ..config import settings
from ..schemas import AuditActor, AuditAppendRequest, CodegenCommitFilesRequest, CodegenCommitFilesResult
from .audit_tools import audit_append

if TYPE_CHECKING:
    from ..couchdb_client import CouchDBClient

GITHUB_API_BASE = "https://api.github.com"
MAX_FILES_PER_REQUEST = 40
MAX_TOTAL_BYTES_PER_REQUEST = 2 * 1024 * 1024
MAX_REF_UPDATE_RETRIES = 3


class CodegenCommitRejected(ValueError):
    """Raised when a codegen.commit_files request fails a safety check.
    Never caught and silently downgraded — every rejection must surface to
    the caller as a real error, not a partial/best-effort commit."""


def _resolve_token() -> str:
    token = os.environ.get("CODEGEN_GIT_TOKEN")
    if not token:
        raise CodegenCommitRejected("CODEGEN_GIT_TOKEN is not set; cannot commit generated code to GitHub")
    return token


def _validate_story_id(story_id: str) -> None:
    if not story_id or "/" in story_id or ".." in story_id or any(ord(c) < 0x20 for c in story_id):
        raise CodegenCommitRejected(f"story_id {story_id!r} is not safe to use as a repo path segment")


def _validate_relative_path(relative_path: str) -> None:
    if not relative_path or relative_path in (".", ".."):
        raise CodegenCommitRejected(f"relative_path {relative_path!r} is empty or not a valid file path")
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("/"):
        raise CodegenCommitRejected(f"relative_path {relative_path!r} must not be absolute")
    if ".." in normalized.split("/"):
        raise CodegenCommitRejected(f"relative_path {relative_path!r} must not contain '..' segments")


def _validate_request_bounds(request: CodegenCommitFilesRequest) -> None:
    if len(request.files) > MAX_FILES_PER_REQUEST:
        raise CodegenCommitRejected(f"request has {len(request.files)} files, exceeding the {MAX_FILES_PER_REQUEST} limit")
    total_bytes = sum(len(f.content.encode("utf-8")) for f in request.files)
    if total_bytes > MAX_TOTAL_BYTES_PER_REQUEST:
        raise CodegenCommitRejected(
            f"request totals {total_bytes} bytes, exceeding the {MAX_TOTAL_BYTES_PER_REQUEST}-byte limit"
        )


def _client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=GITHUB_API_BASE,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )


def _commit_once(client: httpx.Client, owner: str, repo: str, branch: str, story_id: str, request: CodegenCommitFilesRequest) -> CodegenCommitFilesResult:
    ref_response = client.get(f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    ref_response.raise_for_status()
    branch_tip_sha = ref_response.json()["object"]["sha"]

    base_commit_response = client.get(f"/repos/{owner}/{repo}/git/commits/{branch_tip_sha}")
    base_commit_response.raise_for_status()
    base_tree_sha = base_commit_response.json()["tree"]["sha"]

    tree_entries = []
    for file_entry in request.files:
        blob_response = client.post(
            f"/repos/{owner}/{repo}/git/blobs",
            json={"content": base64.b64encode(file_entry.content.encode("utf-8")).decode("ascii"), "encoding": "base64"},
        )
        blob_response.raise_for_status()
        tree_entries.append(
            {
                "path": f"{story_id}/{file_entry.relative_path}",
                "mode": "100644",
                "type": "blob",
                "sha": blob_response.json()["sha"],
            }
        )

    tree_response = client.post(
        f"/repos/{owner}/{repo}/git/trees",
        json={"base_tree": base_tree_sha, "tree": tree_entries},
    )
    tree_response.raise_for_status()
    new_tree_sha = tree_response.json()["sha"]

    commit_response = client.post(
        f"/repos/{owner}/{repo}/git/commits",
        json={"message": request.commit_message, "tree": new_tree_sha, "parents": [branch_tip_sha]},
    )
    commit_response.raise_for_status()
    new_commit = commit_response.json()
    new_commit_sha = new_commit["sha"]

    ref_update_response = client.patch(
        f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
        json={"sha": new_commit_sha},
    )
    if ref_update_response.status_code == 422:
        # The branch moved between our GET and this PATCH (a concurrent
        # commit landed) — the caller retries the whole sequence from the
        # top with a fresh branch tip, same rationale as
        # orchestrator/checkpoint.py's conflict-retry for CouchDB revisions.
        raise _RefMoved()
    ref_update_response.raise_for_status()

    return CodegenCommitFilesResult(
        commit_sha=new_commit_sha,
        commit_url=f"https://github.com/{owner}/{repo}/commit/{new_commit_sha}",
        repo_path=story_id,
    )


class _RefMoved(Exception):
    """Internal signal: the branch ref moved concurrently; retry the commit sequence."""


def codegen_commit_files(
    couchdb_client: "CouchDBClient",
    request: CodegenCommitFilesRequest,
) -> CodegenCommitFilesResult:
    _validate_story_id(request.story_id)
    _validate_request_bounds(request)
    for file_entry in request.files:
        _validate_relative_path(file_entry.relative_path)

    token = _resolve_token()
    owner = settings.codegen_git_repo_owner
    repo = settings.codegen_git_repo_name
    branch = settings.codegen_git_branch
    if not owner or not repo:
        raise CodegenCommitRejected(
            "CODEGEN_GIT_REPO_OWNER/CODEGEN_GIT_REPO_NAME are not configured; cannot commit generated code"
        )

    result: CodegenCommitFilesResult | None = None
    with _client(token) as client:
        for _attempt in range(MAX_REF_UPDATE_RETRIES):
            try:
                result = _commit_once(client, owner, repo, branch, request.story_id, request)
                break
            except _RefMoved:
                continue
        if result is None:
            raise CodegenCommitRejected(
                f"branch {branch!r} moved concurrently {MAX_REF_UPDATE_RETRIES} times; commit aborted"
            )

    audit_append(
        couchdb_client,
        AuditAppendRequest(
            project_id=request.project_id,
            event_category="agent_output",
            actor=AuditActor(kind="agent", id=request.requesting_agent),
            action="codegen_commit_files",
            subject_doc_id=request.story_id,
            subject_doc_rev=None,
            before_state_hash=None,
            after_state_hash=None,
            model_used=None,
            skill_version_hash=None,
        ),
    )

    return result
