from typing import Any, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class LogEntry(BaseModel):
    timestamp: str
    service: str
    region: str
    level: str
    request_id: str
    message: str
    latency_ms: int
    deployment_id: str


class MetricPoint(BaseModel):
    timestamp: str
    service: str
    region: str
    metric: str
    value: str


class DeploymentEvent(BaseModel):
    timestamp: str
    service: str
    region: str
    deployment_id: str
    version: str
    change_summary: str
    changed_files: list[str]


class IncidentBundleResponse(BaseModel):
    incident_id: str
    logs: list[LogEntry]
    metrics: list[MetricPoint]
    deployments: list[DeploymentEvent]
    runbook: str


class IncidentQueryRequest(BaseModel):
    service: str
    region: str
    start_time: str
    end_time: str


class IncidentSummaryResponse(BaseModel):
    incident_id: str
    log_count: int
    metric_count: int
    deployment_count: int
    has_runbook: bool
    error_log_count: int
    affected_services: list[str]
    max_observed_latency_ms: int
    error_patterns: list[str]


class BaselineSignals(BaseModel):
    latency_increase_ratio: float
    latency_spike_detected: bool
    error_rate_increase_ratio: float
    error_rate_spike_detected: bool
    error_patterns: list[str]
    deployment_event_count: int
    deployment_correlation_detected: bool


class EvidenceCoverage(BaseModel):
    has_logs: bool
    has_metrics: bool
    has_deployments: bool
    has_runbook: bool


class EvidenceQuality(BaseModel):
    level: str
    coverage: EvidenceCoverage
    signal_strength: str
    consistency: str
    specificity: str
    time_alignment: str
    data_gaps: list[str]


class BaselineTriageResponse(BaseModel):
    incident_id: str
    affected_services: list[str]
    signals: BaselineSignals
    evidence_quality: EvidenceQuality
    investigation_risk: str
    rule_based_summary: str


class EvidenceChunk(BaseModel):
    citation_id: str
    incident_id: str
    source_type: str
    text: str
    service: Optional[str] = None
    region: Optional[str] = None
    timestamp: Optional[str] = None
    severity: Optional[str] = None


class RetrievalRequest(BaseModel):
    incident_id: str
    query: str
    top_k: int = 5


class RetrievalResponse(BaseModel):
    incident_id: str
    query: str
    chunks: list[EvidenceChunk]


class InvestigationEvidenceResponse(BaseModel):
    incident_id: str
    chunks: list[EvidenceChunk]


class TriageAnalysisRequest(BaseModel):
    incident_id: str
    top_k: int = 10


class IncidentQueryAnalysisRequest(IncidentQueryRequest):
    top_k: int = 10


class TriageAnalysisResponse(BaseModel):
    incident_id: str
    summary: str
    hypothesis: str
    confidence: str
    citations: list[str]
    fallback_reason: Optional[str] = None
    retrieved_chunk_ids: list[str]
    trace_id: str
    analysis_source: str


class LLMAnalysisOutput(BaseModel):
    summary: str
    hypothesis: str
    confidence: str
    citations: list[str]
    fallback_reason: Optional[str] = None


class TraceRecord(BaseModel):
    trace_id: str
    incident_id: str
    input_source: str
    query: Optional[dict[str, Any]] = None
    retrieved_chunk_ids: list[str]
    prompt_version: str
    prompt: str
    model_output: TriageAnalysisResponse
    latency_ms: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    fallback_reason: Optional[str] = None
