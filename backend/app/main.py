from fastapi import FastAPI

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
    IncidentSummaryResponse,
    InvestigationEvidenceResponse,
    RetrievalRequest,
    RetrievalResponse,
)
from app.retrieval import (
    build_evidence_chunks,
    retrieve_chunks,
    retrieve_investigation_evidence,
)


app = FastAPI(
    title="AI Incident Triage Copilot API",
    description="Backend API for evidence-backed AI incident triage.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
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
    return load_incident_bundle(incident_id)


@app.get(
    "/incidents/{incident_id}/summary",
    response_model=IncidentSummaryResponse,
)
def get_incident_summary(incident_id: str) -> IncidentSummaryResponse:
    incident = load_incident_bundle(incident_id)
    return build_incident_summary(incident)


@app.get(
    "/incidents/{incident_id}/baseline-triage",
    response_model=BaselineTriageResponse,
)
def get_baseline_triage(incident_id: str) -> BaselineTriageResponse:
    incident = load_incident_bundle(incident_id)
    return build_baseline_triage(incident)


@app.get(
    "/incidents/{incident_id}/chunks",
    response_model=list[EvidenceChunk],
)
def get_incident_chunks(incident_id: str) -> list[EvidenceChunk]:
    incident = load_incident_bundle(incident_id)
    return build_evidence_chunks(incident)


@app.get(
    "/incidents/{incident_id}/investigation-evidence",
    response_model=InvestigationEvidenceResponse,
)
def get_investigation_evidence(
    incident_id: str,
) -> InvestigationEvidenceResponse:
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
    return load_incident_bundle_from_query(query)


@app.post(
    "/incident-query/baseline-triage",
    response_model=BaselineTriageResponse,
)
def query_incident_baseline_triage(
    query: IncidentQueryRequest,
) -> BaselineTriageResponse:
    incident = load_incident_bundle_from_query(query)
    return build_baseline_triage(incident)


@app.post(
    "/incident-query/chunks",
    response_model=list[EvidenceChunk],
)
def query_incident_chunks(
    query: IncidentQueryRequest,
) -> list[EvidenceChunk]:
    incident = load_incident_bundle_from_query(query)
    return build_evidence_chunks(incident)


@app.post(
    "/incident-query/investigation-evidence",
    response_model=InvestigationEvidenceResponse,
)
def query_investigation_evidence(
    query: IncidentQueryRequest,
) -> InvestigationEvidenceResponse:
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
