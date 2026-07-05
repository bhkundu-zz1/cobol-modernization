"""Shared Pydantic document models mirroring architecture.md section 2.2's CouchDB doc shapes."""

from .audit import AuditActor, AuditEvent, AuditEventCategory
from .backlog import Epic, Story
from .envelope import DocEnvelope
from .job_run import AgentTask, AgentTaskEntry, AgentTaskStatus, JobRun
from .parsed_structure import (
    CallGraph,
    CobolProgramStructure,
    CopybookStructure,
    ExternalCall,
    JclJobStructure,
    JclStep,
    Paragraph,
    SelfCheckPass,
)
from .recommendation import AlternativeConsidered, MigrationRecommendation, RiskAssessment
from .source import Chunk, ScmElementRef, SecretScanResult, SourceFile, SourceUpload

__all__ = [
    "AgentTask",
    "AgentTaskEntry",
    "AgentTaskStatus",
    "AlternativeConsidered",
    "AuditActor",
    "AuditEvent",
    "AuditEventCategory",
    "CallGraph",
    "Chunk",
    "CobolProgramStructure",
    "CopybookStructure",
    "DocEnvelope",
    "Epic",
    "ExternalCall",
    "JclJobStructure",
    "JclStep",
    "JobRun",
    "MigrationRecommendation",
    "Paragraph",
    "RiskAssessment",
    "ScmElementRef",
    "SecretScanResult",
    "SelfCheckPass",
    "SourceFile",
    "SourceUpload",
    "Story",
]
