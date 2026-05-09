from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    name: str
    type: str
    size: int
    updated_at: str
    indexed: bool
    stale: bool = False


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]


class DocumentUploadResponse(BaseModel):
    item: DocumentItem
    message: str


class DocumentPreviewResponse(BaseModel):
    name: str
    type: str
    size: int
    content: str
    character_count: int
    truncated: bool


class IndexStatusResponse(BaseModel):
    ready: bool
    document_count: int
    last_indexed_at: str | None


class IndexTaskStatusResponse(BaseModel):
    state: Literal["idle", "queued", "running", "succeeded", "failed"]
    stage: str
    message: str
    task_id: str | None = None
    queue_depth: int = 0
    document_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class IndexTaskHistoryItem(BaseModel):
    id: int
    task_id: str | None = None
    state: Literal["idle", "queued", "running", "succeeded", "failed"]
    stage: str
    message: str
    document_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    recorded_at: str


class IndexTaskHistoryResponse(BaseModel):
    items: list[IndexTaskHistoryItem]


class RebuildIndexResponse(BaseModel):
    success: bool
    document_count: int
    error: str | None = None


class Citation(BaseModel):
    index: int = 0
    source_id: str = ""
    document_name: str
    snippet: str


class CitationAuditReport(BaseModel):
    source_count: int = 0
    cited_indices: list[int] = Field(default_factory=list)
    uncited_indices: list[int] = Field(default_factory=list)
    invalid_indices: list[int] = Field(default_factory=list)
    citation_coverage: float = 0.0
    status: Literal["pass", "warn", "fail"] = "fail"
    warnings: list[str] = Field(default_factory=list)


class EvidenceFact(BaseModel):
    title: str
    detail: str
    source_indices: list[int] = Field(default_factory=list)


class RiskFlag(BaseModel):
    level: Literal["info", "warning"] = "info"
    message: str
    source_indices: list[int] = Field(default_factory=list)


class EvidencePack(BaseModel):
    query: str = ""
    intent: str = ""
    query_variants: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    retrieval_strategy: str = ""
    ranking_strategy: str = ""
    sources: list[Citation] = Field(default_factory=list)
    key_facts: list[EvidenceFact] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)


class ServiceContext(BaseModel):
    task_type: Literal["consultation_reply", "material_check", "process_guide", "out_of_scope"] = "consultation_reply"
    in_scope: bool = True
    handoff_required: bool = False
    slots: dict[str, str] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    boundary_reason: str = ""


class QaRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class QaResponse(BaseModel):
    answer: str
    content_format: Literal["markdown"] = "markdown"
    sources: list[Citation]
    citation_audit: CitationAuditReport = Field(default_factory=CitationAuditReport)


class ChecklistRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    context: str = Field(default="", max_length=2000)


class ChecklistItem(BaseModel):
    title: str
    details: str
    status: str = "todo"


class ChecklistResponse(BaseModel):
    title: str
    summary: str
    applicability: str
    checklist_items: list[ChecklistItem]
    risk_notes: list[str]
    sources: list[Citation]
    citation_audit: CitationAuditReport = Field(default_factory=CitationAuditReport)


class PrecheckRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    submitted_materials: list[str] = Field(default_factory=list, max_length=30)
    context: str = Field(default="", max_length=2000)


class PrecheckItem(BaseModel):
    name: str
    status: Literal["provided", "missing", "review"]
    detail: str
    matched_material: str | None = None


class WorkflowRequest(BaseModel):
    task: str = Field(min_length=1, max_length=1000)
    submitted_materials: list[str] = Field(default_factory=list, max_length=30)
    context: str = Field(default="", max_length=2000)


class WorkflowStep(BaseModel):
    key: str
    title: str
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    detail: str


class WorkflowResponse(BaseModel):
    intent: Literal["checklist", "policy_answer", "out_of_scope"]
    answer: str
    content_format: Literal["markdown"] = "markdown"
    steps: list[WorkflowStep]
    sources: list[Citation]
    service_context: ServiceContext = Field(default_factory=ServiceContext)
    evidence_pack: EvidencePack = Field(default_factory=EvidencePack)
    citation_audit: CitationAuditReport = Field(default_factory=CitationAuditReport)


class PrecheckResponse(BaseModel):
    title: str
    summary: str
    verdict: Literal["pass", "warn", "fail"]
    applicability: str
    answer: str
    content_format: Literal["markdown"] = "markdown"
    submitted_materials: list[str] = Field(default_factory=list)
    review_items: list[PrecheckItem] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    steps: list[WorkflowStep] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    service_context: ServiceContext = Field(default_factory=ServiceContext)
    evidence_pack: EvidencePack = Field(default_factory=EvidencePack)
    citation_audit: CitationAuditReport = Field(default_factory=CitationAuditReport)


class HealthComponent(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    document_count: int = 0
    index_ready: bool = False
    last_indexed_at: str | None = None
    active_task_state: Literal["idle", "queued", "running", "succeeded", "failed"] = "idle"
    components: list[HealthComponent] = Field(default_factory=list)


class InteractionHistoryItem(BaseModel):
    id: int
    kind: Literal["qa", "checklist", "workflow", "precheck"]
    prompt: str
    context: str = ""
    intent: str = ""
    answer_preview: str
    source_count: int = 0
    citation_coverage: float = 0.0
    status: Literal["pass", "warn", "fail"] = "fail"
    created_at: str


class InteractionHistoryResponse(BaseModel):
    items: list[InteractionHistoryItem]


class EvalCase(BaseModel):
    question: str
    expected_documents: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)


class EvalCaseResult(BaseModel):
    question: str
    passed: bool
    expected_documents: list[str]
    retrieved_documents: list[str]
    retrieval_hit: bool
    keyword_coverage: float
    source_keyword_coverage: float = 0.0
    citation_coverage: float
    answer_preview: str
    warnings: list[str] = Field(default_factory=list)


class EvalReport(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    retrieval_hit_rate: float
    keyword_coverage_rate: float
    source_keyword_coverage_rate: float = 0.0
    citation_coverage_rate: float
    results: list[EvalCaseResult]
