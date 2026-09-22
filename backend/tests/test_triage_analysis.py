from app.incident_loader import load_incident_bundle
from app.models import LLMAnalysisOutput, LLMGenerationResult
from app.triage_analysis import (
    build_triage_analysis,
    validate_analysis_output,
)


def test_generation_failure_uses_deterministic_fallback(monkeypatch) -> None:
    def fake_generate_llm_analysis(prompt: str) -> LLMGenerationResult:
        return LLMGenerationResult(
            failure_code="api_timeout",
            failure_message="OpenAI request timed out.",
        )

    monkeypatch.setattr(
        "app.triage_analysis.generate_llm_analysis",
        fake_generate_llm_analysis,
    )
    incident = load_incident_bundle("checkout_latency_spike")

    result = build_triage_analysis(incident, top_k=10)

    assert result.analysis_source == "deterministic_fallback"
    assert result.llm_failure_code == "api_timeout"
    assert result.confidence == "low"
    assert "OpenAI request timed out." in result.fallback_reason


def test_all_invalid_citations_reject_llm_output() -> None:
    output = LLMAnalysisOutput(
        summary="Checkout requests are failing.",
        hypothesis="A database issue is a candidate cause.",
        confidence="high",
        citations=["fake-999"],
    )

    result = validate_analysis_output(
        output=output,
        evidence_quality_level="strong",
        retrieved_chunk_ids=["log-001", "metric-001"],
    )

    assert result is None


def test_evidence_quality_caps_llm_confidence() -> None:
    output = LLMAnalysisOutput(
        summary="Checkout requests are slow.",
        hypothesis="A database issue is a candidate cause.",
        confidence="high",
        citations=["log-001"],
    )

    result = validate_analysis_output(
        output=output,
        evidence_quality_level="medium",
        retrieved_chunk_ids=["log-001"],
    )

    assert result is not None
    assert result.confidence == "medium"
    assert result.fallback_reason is not None
