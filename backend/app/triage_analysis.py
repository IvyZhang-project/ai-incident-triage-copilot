from typing import Optional

from app.incident_analysis import build_baseline_triage, build_incident_summary
from app.llm_client import generate_llm_analysis
from app.models import (
    EvidenceChunk,
    IncidentBundleResponse,
    LLMAnalysisOutput,
    TriageAnalysisResponse,
)
from app.retrieval import retrieve_investigation_evidence
from app.traces import new_trace_id


CONFIDENCE_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
}
EVIDENCE_QUALITY_CONFIDENCE_CAP = {
    "weak": "low",
    "medium": "medium",
    "strong": "high",
}


def build_analysis_summary(incident: IncidentBundleResponse) -> str:
    summary = build_incident_summary(incident)
    affected_services = (
        ", ".join(summary.affected_services)
        if summary.affected_services
        else "no services with matching logs"
    )

    return (
        f"Incident {incident.incident_id} includes {summary.error_log_count} "
        f"ERROR logs across {affected_services}. "
        f"Max observed request latency is "
        f"{summary.max_observed_latency_ms}ms."
    )


def select_citation_ids(chunks: list[EvidenceChunk]) -> list[str]:
    return [chunk.citation_id for chunk in chunks]


def determine_fallback_reason(evidence_quality_level: str) -> Optional[str]:
    if evidence_quality_level == "strong":
        return None

    return (
        "Evidence is not strong enough for a high-confidence root-cause claim. "
        "Treat this as a candidate hypothesis for human review."
    )


def cap_confidence(
    llm_confidence: str,
    evidence_quality_level: str,
) -> str:
    normalized_confidence = llm_confidence.lower()
    max_confidence = EVIDENCE_QUALITY_CONFIDENCE_CAP[evidence_quality_level]

    if normalized_confidence not in CONFIDENCE_RANK:
        return "low"

    if CONFIDENCE_RANK[normalized_confidence] > CONFIDENCE_RANK[max_confidence]:
        return max_confidence

    return normalized_confidence


def filter_valid_citations(
    requested_citations: list[str],
    allowed_citation_ids: list[str],
) -> list[str]:
    allowed_ids = set(allowed_citation_ids)

    return [
        citation_id
        for citation_id in requested_citations
        if citation_id in allowed_ids
    ]


def filter_invalid_citations(
    requested_citations: list[str],
    allowed_citation_ids: list[str],
) -> list[str]:
    allowed_ids = set(allowed_citation_ids)

    return [
        citation_id
        for citation_id in requested_citations
        if citation_id not in allowed_ids
    ]


def append_fallback_reason(
    existing_reason: Optional[str],
    new_reason: str,
) -> str:
    if existing_reason:
        return existing_reason + " " + new_reason

    return new_reason


def build_deterministic_analysis_output(
    incident: IncidentBundleResponse,
    rule_based_summary: str,
    evidence_quality_level: str,
    retrieved_chunk_ids: list[str],
    validation_failure_reason: Optional[str] = None,
) -> LLMAnalysisOutput:
    fallback_reason = (
        "LLM generation was unavailable or invalid, so the system returned a "
        "deterministic evidence assessment instead of a generated root-cause "
        "hypothesis."
    )
    if validation_failure_reason is not None:
        fallback_reason += " " + validation_failure_reason

    evidence_quality_fallback_reason = determine_fallback_reason(
        evidence_quality_level
    )
    if evidence_quality_fallback_reason is not None:
        fallback_reason += " " + evidence_quality_fallback_reason

    return LLMAnalysisOutput(
        summary=build_analysis_summary(incident),
        hypothesis=rule_based_summary,
        confidence="low",
        citations=retrieved_chunk_ids,
        fallback_reason=fallback_reason,
    )


def validate_analysis_output(
    output: LLMAnalysisOutput,
    evidence_quality_level: str,
    retrieved_chunk_ids: list[str],
) -> Optional[LLMAnalysisOutput]:
    confidence = cap_confidence(output.confidence, evidence_quality_level)
    citations = filter_valid_citations(output.citations, retrieved_chunk_ids)
    invalid_citations = filter_invalid_citations(
        output.citations,
        retrieved_chunk_ids,
    )

    if not citations:
        return None

    fallback_reason = output.fallback_reason
    if invalid_citations:
        if CONFIDENCE_RANK[confidence] > CONFIDENCE_RANK["medium"]:
            confidence = "medium"

        fallback_reason = append_fallback_reason(
            fallback_reason,
            (
                "The LLM cited evidence that was not retrieved, so invalid "
                "citations were removed and confidence was downgraded."
            ),
        )

    if confidence != "high" and fallback_reason is None:
        fallback_reason = determine_fallback_reason(evidence_quality_level)

    return LLMAnalysisOutput(
        summary=output.summary,
        hypothesis=output.hypothesis,
        confidence=confidence,
        citations=citations,
        fallback_reason=fallback_reason,
    )


def build_analysis_prompt(
    incident: IncidentBundleResponse,
    retrieved_chunks: list[EvidenceChunk],
) -> str:
    evidence_lines = [
        f"{chunk.citation_id}: {chunk.text}"
        for chunk in retrieved_chunks
    ]

    return (
        "You are an incident triage assistant. Use only the cited evidence "
        "below to produce a concise incident summary, root-cause hypothesis, "
        "confidence, citations, and fallback reason when evidence is weak.\n\n"
        "Return JSON only with this exact shape:\n"
        "{\n"
        '  "summary": "short incident summary",\n'
        '  "hypothesis": "candidate root-cause hypothesis",\n'
        '  "confidence": "low | medium | high",\n'
        '  "citations": ["citation-id"],\n'
        '  "fallback_reason": "reason or null"\n'
        "}\n\n"
        "Rules:\n"
        "- Use only citation IDs from the evidence below.\n"
        "- Do not invent services, metrics, logs, deployments, or causes.\n"
        "- If evidence is weak or conflicting, use low/medium confidence and "
        "include a fallback reason.\n\n"
        f"Incident ID: {incident.incident_id}\n\n"
        "Evidence:\n"
        + "\n".join(evidence_lines)
    )


def build_triage_analysis(
    incident: IncidentBundleResponse,
    top_k: int,
) -> TriageAnalysisResponse:
    baseline = build_baseline_triage(incident)
    retrieved_chunks = retrieve_investigation_evidence(incident, top_k=top_k)
    retrieved_chunk_ids = select_citation_ids(retrieved_chunks)
    prompt = build_analysis_prompt(incident, retrieved_chunks)
    llm_result = generate_llm_analysis(prompt)
    llm_output = llm_result.output
    llm_failure_code = llm_result.failure_code

    if llm_output is None:
        analysis_source = "deterministic_fallback"
        analysis_output = build_deterministic_analysis_output(
            incident=incident,
            rule_based_summary=baseline.rule_based_summary,
            evidence_quality_level=baseline.evidence_quality.level,
            retrieved_chunk_ids=retrieved_chunk_ids,
            validation_failure_reason=llm_result.failure_message,
        )
    else:
        analysis_source = "llm"
        analysis_output = validate_analysis_output(
            output=llm_output,
            evidence_quality_level=baseline.evidence_quality.level,
            retrieved_chunk_ids=retrieved_chunk_ids,
        )
        if analysis_output is None:
            analysis_source = "deterministic_fallback"
            llm_failure_code = "citation_validation_error"
            analysis_output = build_deterministic_analysis_output(
                incident=incident,
                rule_based_summary=baseline.rule_based_summary,
                evidence_quality_level=baseline.evidence_quality.level,
                retrieved_chunk_ids=retrieved_chunk_ids,
                validation_failure_reason=(
                    "The LLM response did not cite any retrieved evidence."
                ),
            )

    return TriageAnalysisResponse(
        incident_id=incident.incident_id,
        summary=analysis_output.summary,
        hypothesis=analysis_output.hypothesis,
        confidence=analysis_output.confidence,
        citations=analysis_output.citations,
        fallback_reason=analysis_output.fallback_reason,
        retrieved_chunk_ids=retrieved_chunk_ids,
        trace_id=new_trace_id(),
        analysis_source=analysis_source,
        llm_failure_code=llm_failure_code,
    )
