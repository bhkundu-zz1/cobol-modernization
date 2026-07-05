"""Common document envelope fields shared by every CouchDB document type.

Per architecture.md section 2.1: every document carries these fields at
minimum, regardless of `type`. Modeled as a mixin so each concrete document
model (SourceUpload, CobolProgramStructure, etc.) inherits it rather than
repeating the fields.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocEnvelope(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    rev: str | None = Field(default=None, alias="_rev")
    type: str
    schema_version: int = 1
    project_id: str
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str
    updated_at: datetime = Field(default_factory=utcnow)
    trace_id: str

    model_config = {"populate_by_name": True}
