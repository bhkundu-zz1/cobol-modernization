"""Structural-extraction document models (architecture.md section 2.2).

CobolProgramStructure is real this pass (produced by
agents/cobol_structural). JclJobStructure and CopybookStructure are
schema-complete but unused by real logic this pass — see
docs/deferred_scope.md.
"""

from typing import Literal

from pydantic import BaseModel

from .envelope import DocEnvelope


class Paragraph(BaseModel):
    name: str
    calls: list[str] = []
    performs: list[str] = []


class ExternalCall(BaseModel):
    target: str
    call_type: str
    resolved: bool = False


class CallGraph(BaseModel):
    nodes: list[str] = []
    edges: list[dict] = []
    confidence: float = 0.0


class SelfCheckPass(BaseModel):
    performed: bool = False
    discrepancies_found: int = 0
    resolved: bool = False


class CobolProgramStructure(DocEnvelope):
    type: Literal["cobol_program_structure"] = "cobol_program_structure"
    source_file_id: str
    program_id: str
    divisions: dict = {}
    copybooks_referenced: list[str] = []
    paragraphs: list[Paragraph] = []
    call_graph: CallGraph = CallGraph()
    external_calls: list[ExternalCall] = []
    extraction_method: Literal["llm_native_chunked"] = "llm_native_chunked"
    chunks_used: int
    self_check_pass: SelfCheckPass = SelfCheckPass()
    confidence_score: float
    needs_human_review: bool
    plain_english_summary: str | None = None


class JclStep(BaseModel):
    step_name: str
    exec_pgm: str | None = None
    cond_codes: list[str] = []
    dd_statements: list[dict] = []


class JclJobStructure(DocEnvelope):
    """Schema-complete; not populated by real logic this pass (stub agent)."""

    type: Literal["jcl_job_structure"] = "jcl_job_structure"
    source_file_id: str
    job_name: str
    steps: list[JclStep] = []
    step_dependency_graph: dict = {}
    procs_referenced: list[str] = []
    schedule_hint_detected: str | None = None
    confidence_score: float = 0.0


class CopybookStructure(DocEnvelope):
    """Schema-complete; not populated by real logic this pass."""

    type: Literal["copybook_structure"] = "copybook_structure"
    source_file_id: str
    fields: list[dict] = []
