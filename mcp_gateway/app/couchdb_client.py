"""Thin ibmcloudant wrapper — the ONLY module in this repo allowed to import ibmcloudant.

Every other component (agents, core services) reaches CouchDB exclusively
through the MCP gateway's couchdb.read/couchdb.write tools (architecture.md
section 1, "Connection rules") — this client is that tool's implementation
detail, never imported directly outside mcp_gateway.
"""

from typing import Any

from ibmcloudant.cloudant_v1 import CloudantV1, DesignDocument, Document
from ibm_cloud_sdk_core.authenticators import BasicAuthenticator

from .config import settings


class CouchDBClient:
    def __init__(self) -> None:
        authenticator = BasicAuthenticator(settings.couchdb_user, settings.couchdb_password)
        self._client = CloudantV1(authenticator=authenticator)
        self._client.set_service_url(settings.couchdb_url)

    def ensure_database(self, db_name: str) -> None:
        try:
            self._client.get_database_information(db=db_name).get_result()
        except Exception:
            self._client.put_database(db=db_name).get_result()

    def get_document(self, db_name: str, doc_id: str) -> dict[str, Any] | None:
        try:
            return self._client.get_document(db=db_name, doc_id=doc_id).get_result()
        except Exception:
            return None

    def put_document(self, db_name: str, doc: dict[str, Any]) -> dict[str, Any]:
        document = Document.from_dict(doc)
        result = self._client.post_document(db=db_name, document=document).get_result()
        return {"id": result["id"], "rev": result["rev"]}

    def find(self, db_name: str, selector: dict[str, Any], limit: int = 50) -> dict[str, Any]:
        result = self._client.post_find(db=db_name, selector=selector, limit=limit).get_result()
        return {"docs": result.get("docs", []), "bookmark": result.get("bookmark")}

    def create_index(self, db_name: str, index_def: dict[str, Any], index_name: str) -> None:
        self._client.post_index(db=db_name, index=index_def, name=index_name).get_result()

    def put_design_document(self, db_name: str, design_doc_id: str, design_doc: dict[str, Any]) -> None:
        # Design docs (_design/xxx) are rejected by the generic
        # get_document/post_document SDK calls (ibmcloudant validates doc
        # IDs and rejects a leading underscore outside its own reserved
        # methods) — use the SDK's dedicated design-document methods
        # instead, confirmed against a live CouchDB 3.3 instance.
        ddoc_name = design_doc_id.removeprefix("_design/")
        try:
            existing = self._client.get_design_document(db=db_name, ddoc=ddoc_name).get_result()
            design_doc["_rev"] = existing["_rev"]
        except Exception:
            pass

        document = DesignDocument.from_dict(design_doc)
        self._client.put_design_document(db=db_name, ddoc=ddoc_name, design_document=document).get_result()


_client: CouchDBClient | None = None


def get_couchdb_client() -> CouchDBClient:
    global _client
    if _client is None:
        _client = CouchDBClient()
    return _client
