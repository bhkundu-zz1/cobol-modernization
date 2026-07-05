"""Source ingestion document models (architecture.md section 2.2).

SourceUpload / SourceFile / Chunk are produced identically whether the
source came from a manual upload or a mainframe SCM connector pull
(architecture.md section 1a) — `source_origin` and `scm_element_ref`
distinguish the two, not a parallel schema.
"""

from typing import Literal

from pydantic import BaseModel

from .envelope import DocEnvelope


class SecretScanResult(BaseModel):
    flagged_files: list[str] = []
    scan_passed: bool = False


class ScmElementRef(BaseModel):
    tool: Literal["endevor", "panvalet", "changeman", "mock"]
    system: str
    subsystem: str
    type: str
    element_id: str
    version: str | None = None


class SourceUpload(DocEnvelope):
    type: Literal["source_upload"] = "source_upload"
    uploaded_by: str
    upload_batch_id: str
    source_origin: Literal["manual_upload", "mainframe_scm"]
    file_count: int
    total_bytes: int
    status: Literal["received", "scanning", "ready_for_pipeline", "failed"]
    secret_scan_result: SecretScanResult = SecretScanResult()


class SourceFile(DocEnvelope):
    type: Literal["source_file"] = "source_file"
    upload_batch_id: str
    filename: str
    language: Literal["cobol", "jcl", "copybook"]
    sha256: str
    line_count: int
    chunking_required: bool
    source_origin: Literal["manual_upload", "mainframe_scm"]
    scm_element_ref: ScmElementRef | None = None
    source_text: str | None = None
    relative_path: str | None = None


class Chunk(DocEnvelope):
    type: Literal["chunk"] = "chunk"
    source_file_id: str
    chunk_index: int
    of_chunks: int
    chunk_strategy: str
    overlap_lines: int
    start_line: int
    end_line: int
