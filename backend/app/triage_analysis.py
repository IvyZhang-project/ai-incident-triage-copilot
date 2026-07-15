from typing import Optional

from app.incident_analysis import build_baseline_triage, build_incident_summary
from app.models import (
    EvidenceChunk,
    IncidentBundleResponse,
    TriageAnalysisResponse,
)
from app.retrieval import retrieve_investigation_evidence
from app.traces import new_trace_id


def build_analysis_summary(incident: IncidentBundleResponse) -> str:
    summary = build_incident_summary(incident)

    return (
        f"Incident {incident.incident_id} includes {summary.error_log_count} "
        f"ERROR logs across {', '.join(summary.affected_services)}. "
        f"Max observed request latency is "
        f"{summary.max_observed_latency_ms}ms."
    )


def select_citation_ids(chunks: list[EvidenceChunk]) -> list[str]:
    return [chunk.citation_id for chunk in chunks]


def determine_fallback_reason(evidence_strength: str) -> Optional[str]:
    if evidence_strength == "high":
        return None

    return (
        "Evidence is not strong enough for a high-confidence root-cause claim. "
        "Treat this as a candidate hypothesis for human review."
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

    return TriageAnalysisResponse(
        incident_id=incident.incident_id,
        summary=build_analysis_summary(incident),
        hypothesis=baseline.rule_based_hypothesis,
        confidence=baseline.evidence_strength,
        citations=retrieved_chunk_ids,
        fallback_reason=determine_fallback_reason(baseline.evidence_strength),
        retrieved_chunk_ids=retrieved_chunk_ids,
        trace_id=new_trace_id(),
    )
