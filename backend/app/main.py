from fastapi import FastAPI

from app.incident_analysis import build_baseline_triage, build_incident_summary
from app.incident_loader import load_incident_bundle
from app.models import (
    BaselineTriageResponse,
    HealthResponse,
    IncidentBundleResponse,
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
