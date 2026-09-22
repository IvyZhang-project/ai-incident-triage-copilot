import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import LLMGenerationResult
from app.traces import TRACE_STORE


@pytest.fixture
def client() -> TestClient:
    TRACE_STORE.clear()
    with TestClient(app) as test_client:
        yield test_client
    TRACE_STORE.clear()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-incident-triage-copilot",
        "version": "0.1.0",
    }


def test_curated_incident_endpoint_returns_complete_bundle(
    client: TestClient,
) -> None:
    response = client.get("/incidents/checkout_latency_spike")

    assert response.status_code == 200
    body = response.json()
    assert body["incident_id"] == "checkout_latency_spike"
    assert body["logs"]
    assert body["metrics"]
    assert body["deployments"]
    assert body["runbook"]
    assert "eval_label" not in body


def test_incident_query_filters_service_region_and_time_window(
    client: TestClient,
) -> None:
    response = client.post(
        "/incident-query",
        json={
            "service": "checkout-api",
            "region": "us-west-2",
            "start_time": "2026-06-15T09:30:00Z",
            "end_time": "2026-06-15T09:40:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["logs"]) == 4
    assert len(body["metrics"]) == 6
    assert len(body["deployments"]) == 1

    records = body["logs"] + body["metrics"] + body["deployments"]
    assert all(record["service"] == "checkout-api" for record in records)
    assert all(record["region"] == "us-west-2" for record in records)
    assert all(
        "2026-06-15T09:30:00Z"
        <= record["timestamp"]
        <= "2026-06-15T09:40:00Z"
        for record in records
    )


def test_incident_query_rejects_missing_required_fields(
    client: TestClient,
) -> None:
    response = client.post(
        "/incident-query",
        json={"service": "checkout-api"},
    )

    assert response.status_code == 422


def test_retrieval_only_eval_endpoint_runs_offline(
    client: TestClient,
) -> None:
    response = client.post(
        "/eval/run",
        json={"run_analysis": False, "top_k": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_cases"] == 6
    assert body["retrieval_accuracy"] == 1.0
    assert body["citation_correctness"] is None


def test_unknown_trace_returns_not_found(client: TestClient) -> None:
    response = client.get("/traces/trace-does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Trace not found"}


def test_triage_endpoint_falls_back_and_saves_trace(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_generate_llm_analysis(prompt: str) -> LLMGenerationResult:
        return LLMGenerationResult(
            failure_code="api_timeout",
            failure_message="OpenAI request timed out.",
        )

    monkeypatch.setattr(
        "app.triage_analysis.generate_llm_analysis",
        fake_generate_llm_analysis,
    )

    analysis_response = client.post(
        "/triage/analyze",
        json={"incident_id": "checkout_latency_spike", "top_k": 10},
    )

    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["analysis_source"] == "deterministic_fallback"
    assert analysis["llm_failure_code"] == "api_timeout"

    trace_response = client.get(f"/traces/{analysis['trace_id']}")

    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["trace_id"] == analysis["trace_id"]
    assert trace["llm_failure_code"] == "api_timeout"
    assert trace["model_output"] == analysis
