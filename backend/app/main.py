from fastapi import FastAPI

from app.incident_analysis import build_baseline_triage, build_incident_summary
from app.incident_loader import (
    load_incident_bundle,
    load_incident_bundle_from_query,
)
from app.models import (
    BaselineTriageResponse,
    HealthResponse,
    IncidentBundleResponse,
    IncidentQueryRequest,
    IncidentSummaryResponse,
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
