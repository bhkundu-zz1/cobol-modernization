"""Shared in-memory test doubles for CouchDB and Redis.

No real network/server dependency: exercises the tool logic in
mcp_gateway/app/tools/* against fakes that implement just the subset of the
CouchDBClient / redis.Redis surface those tools actually call.
"""

import copy
import uuid
from typing import Any

import pytest


class FakeCouchDBClient:
    """In-memory stand-in for mcp_gateway.app.couchdb_client.CouchDBClient."""

    def __init__(self) -> None:
        self._dbs: dict[str, dict[str, dict[str, Any]]] = {}

    def ensure_database(self, db_name: str) -> None:
        self._dbs.setdefault(db_name, {})

    def get_document(self, db_name: str, doc_id: str) -> dict[str, Any] | None:
        doc = self._dbs.get(db_name, {}).get(doc_id)
        return copy.deepcopy(doc) if doc is not None else None

    def put_document(self, db_name: str, doc: dict[str, Any]) -> dict[str, Any]:
        self.ensure_database(db_name)
        doc = copy.deepcopy(doc)
        doc_id = doc.get("_id") or str(uuid.uuid4())
        doc["_id"] = doc_id
        prev_rev_num = 0
        if doc_id in self._dbs[db_name]:
            prev_rev = self._dbs[db_name][doc_id].get("_rev", "0-x")
            prev_rev_num = int(prev_rev.split("-")[0])
        new_rev = f"{prev_rev_num + 1}-fake"
        doc["_rev"] = new_rev
        self._dbs[db_name][doc_id] = doc
        return {"id": doc_id, "rev": new_rev}

    def find(self, db_name: str, selector: dict[str, Any], limit: int = 50) -> dict[str, Any]:
        docs = list(self._dbs.get(db_name, {}).values())
        matched = [d for d in docs if _matches(d, selector)]
        return {"docs": copy.deepcopy(matched[:limit]), "bookmark": None}

    def create_index(self, db_name: str, index_def: dict[str, Any], index_name: str) -> None:
        pass  # no-op: the fake has no index concept, `find` does a full scan

    def put_design_document(self, db_name: str, design_doc_id: str, design_doc: dict[str, Any]) -> None:
        self.put_document(db_name, {**design_doc, "_id": design_doc_id})


def _matches(doc: dict[str, Any], selector: dict[str, Any]) -> bool:
    for key, expected in selector.items():
        actual = doc.get(key)
        if isinstance(expected, dict):
            for op, val in expected.items():
                if op == "$gte" and not (actual is not None and actual >= val):
                    return False
                if op == "$lte" and not (actual is not None and actual <= val):
                    return False
        elif actual != expected:
            return False
    return True


class FakeRedis:
    """In-memory stand-in for redis.Redis, implementing only get/set."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.fixture
def fake_couchdb() -> FakeCouchDBClient:
    return FakeCouchDBClient()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()
