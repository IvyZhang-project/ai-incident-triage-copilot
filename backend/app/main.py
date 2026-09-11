from fastapi import FastAPI, HTTPException

from app.env_loader import load_dotenv
from app.incident_analysis import build_baseline_triage, build_incident_summary
from app.incident_loader import (
    load_incident_bundle,
    load_incident_bundle_from_query,
)
from app.models import (
    BaselineTriageResponse,
    EvidenceChunk,
    HealthResponse,
    IncidentBundleResponse,
    IncidentQueryRequest,
    IncidentQueryAnalysisRequest,
    IncidentSummaryResponse,
    InvestigationEvidenceResponse,
    RetrievalRequest,
    RetrievalResponse,
    TriageAnalysisRequest,
    TriageAnalysisResponse,
    TraceRecord,
)
from app.retrieval import (
    build_evidence_chunks,
    retrieve_chunks,
    retrieve_investigation_evidence,
)
from app.traces import calculate_latency_ms, get_trace, save_trace, start_timer
from app.triage_analysis import build_analysis_prompt, build_triage_analysis


load_dotenv()

app = FastAPI(
    title="AI Incident Triage Copilot API",
    description="Backend API for evidence-backed AI incident triage.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a lightweight service health check for uptime monitoring."""
    return HealthResponse(
        status="ok",
        service="ai-incident-triage-copilot",
        version="0.1.0",
    )


@app.get(
    "/incidents/{incident_id}",
    response_model=IncidentBundleResponse,
)
def get_incident(incident_id: str) -> IncidentBundleResponse:
    """Load a curated incident fixture by ID as a complete evidence bundle."""
    return load_incident_bundle(incident_id)


@app.get(
    "/incidents/{incident_id}/summary",
    response_model=IncidentSummaryResponse,
)
def get_incident_summary(incident_id: str) -> IncidentSummaryResponse:
    """
    Summarize high-level counts and simple signals for a curated incident.

    Example: use this to quickly inspect log count, ERROR count, affected
    services, max observed latency, and detected error patterns.
    """
    incident = load_incident_bundle(incident_id)
    return build_incident_summary(incident)


@app.get(
    "/incidents/{incident_id}/baseline-triage",
    response_model=BaselineTriageResponse,
)
def get_baseline_triage(incident_id: str) -> BaselineTriageResponse:
    """
    Run deterministic baseline triage on a curated incident fixture.

    Example: use this to check latency spike, error-rate spike, deployment
    correlation, evidence strength, missing evidence, and rule-based hypothesis.
    """
    incident = load_incident_bundle(incident_id)
    return build_baseline_triage(incident)


@app.get(
    "/incidents/{incident_id}/chunks",
    response_model=list[EvidenceChunk],
)
def get_incident_chunks(incident_id: str) -> list[EvidenceChunk]:
    """Convert a curated incident bundle into citation-ready evidence chunks."""
    incident = load_incident_bundle(incident_id)
    return build_evidence_chunks(incident)


@app.get(
    "/incidents/{incident_id}/investigation-evidence",
    response_model=InvestigationEvidenceResponse,
)
def get_investigation_evidence(
    incident_id: str,
) -> InvestigationEvidenceResponse:
    """Rank high-signal investigation evidence for a curated incident."""
    incident = load_incident_bundle(incident_id)
    chunks = retrieve_investigation_evidence(incident)

    return InvestigationEvidenceResponse(
        incident_id=incident.incident_id,
        chunks=chunks,
    )


@app.post(
    "/incident-query",
    response_model=IncidentBundleResponse,
)
def query_incident(
    query: IncidentQueryRequest,
) -> IncidentBundleResponse:
    """Filter mixed local data into a clean incident evidence bundle."""
    return load_incident_bundle_from_query(query)


@app.post(
    "/incident-query/summary",
    response_model=IncidentSummaryResponse,
)
def query_incident_summary(
    query: IncidentQueryRequest,
) -> IncidentSummaryResponse:
    """
    Summarize high-level counts and simple signals after filtering mixed data.

    Example: use this to inspect whether a service, region, and time-window
    query found the expected logs, metrics, deployments, and error patterns.
    """
    incident = load_incident_bundle_from_query(query)
    return build_incident_summary(incident)


@app.post(
    "/incident-query/baseline-triage",
    response_model=BaselineTriageResponse,
)
def query_incident_baseline_triage(
    query: IncidentQueryRequest,
) -> BaselineTriageResponse:
    """Run deterministic baseline triage after filtering mixed incident data."""
    incident = load_incident_bundle_from_query(query)
    return build_baseline_triage(incident)


@app.post(
    "/incident-query/chunks",
    response_model=list[EvidenceChunk],
)
def query_incident_chunks(
    query: IncidentQueryRequest,
) -> list[EvidenceChunk]:
    """Filter mixed data and convert the result into evidence chunks."""
    incident = load_incident_bundle_from_query(query)
    return build_evidence_chunks(incident)


@app.post(
    "/incident-query/investigation-evidence",
    response_model=InvestigationEvidenceResponse,
)
def query_investigation_evidence(
    query: IncidentQueryRequest,
) -> InvestigationEvidenceResponse:
    """Filter mixed data and return ranked evidence for initial triage."""
    incident = load_incident_bundle_from_query(query)
    chunks = retrieve_investigation_evidence(incident)

    return InvestigationEvidenceResponse(
        incident_id=incident.incident_id,
        chunks=chunks,
    )


@app.post(
    "/retrieve",
    response_model=RetrievalResponse,
)
def retrieve_incident_chunks(
    request: RetrievalRequest,
) -> RetrievalResponse:
    """Run question-specific retrieval against a curated incident fixture."""
    incident = load_incident_bundle(request.incident_id)
    chunks = retrieve_chunks(
        incident=incident,
        query=request.query,
        top_k=request.top_k,
    )

    return RetrievalResponse(
        incident_id=incident.incident_id,
        query=request.query,
        chunks=chunks,
    )


@app.post(
    "/triage/analyze",
    response_model=TriageAnalysisResponse,
)
def analyze_incident(
    request: TriageAnalysisRequest,
) -> TriageAnalysisResponse:
    """Analyze a curated incident and save a trace for debugging."""
    start_time = start_timer()
    incident = load_incident_bundle(request.incident_id)
    analysis = build_triage_analysis(
        incident=incident,
        top_k=request.top_k,
    )
    retrieved_chunks = retrieve_investigation_evidence(
        incident,
        top_k=request.top_k,
    )
    prompt = build_analysis_prompt(incident, retrieved_chunks)
    save_trace(
        incident_id=incident.incident_id,
        input_source="curated_incident",
        prompt=prompt,
        analysis=analysis,
        latency_ms=calculate_latency_ms(start_time),
    )

    return analysis


@app.post(
    "/incident-query/triage/analyze",
    response_model=TriageAnalysisResponse,
)
def analyze_queried_incident(
    request: IncidentQueryAnalysisRequest,
) -> TriageAnalysisResponse:
    """Filter mixed data, analyze the incident, and save a debug trace."""
    start_time = start_timer()
    incident = load_incident_bundle_from_query(request)
    analysis = build_triage_analysis(
        incident=incident,
        top_k=request.top_k,
    )
    retrieved_chunks = retrieve_investigation_evidence(
        incident,
        top_k=request.top_k,
    )
    prompt = build_analysis_prompt(incident, retrieved_chunks)
    save_trace(
        incident_id=incident.incident_id,
        input_source="mixed_incident_query",
        query=request.model_dump(),
        prompt=prompt,
        analysis=analysis,
        latency_ms=calculate_latency_ms(start_time),
    )

    return analysis


@app.get(
    "/traces/{trace_id}",
    response_model=TraceRecord,
)
def get_trace_record(trace_id: str) -> TraceRecord:
    """Return the stored debug trace for a previous triage analysis."""
    trace = get_trace(trace_id)

    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    return trace
