import json
import re
from pathlib import Path
from statistics import mean
from typing import Optional

from app.incident_loader import PROJECT_ROOT, load_incident_bundle
from app.models import (
    EvalCase,
    EvalCaseResult,
    EvalRunRequest,
    EvalRunResponse,
    TriageAnalysisResponse,
)
from app.retrieval import retrieve_investigation_evidence


EVAL_CASES_PATH = PROJECT_ROOT / "data" / "eval_cases" / "eval_cases.json"


def load_eval_cases() -> list[EvalCase]:
    with EVAL_CASES_PATH.open() as file:
        return [EvalCase(**case) for case in json.load(file)]


def normalize_text(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(normalized.split())


def term_matches_text(term: str, text: str) -> bool:
    return normalize_text(term) in normalize_text(text)


def find_matching_terms(terms: list[str], text: str) -> list[str]:
    return [term for term in terms if term_matches_text(term, text)]


def find_missing_terms(terms: list[str], text: str) -> list[str]:
    return [term for term in terms if not term_matches_text(term, text)]


def evaluate_citations(
    analysis: TriageAnalysisResponse,
) -> bool:
    retrieved_ids = set(analysis.retrieved_chunk_ids)
    return all(citation_id in retrieved_ids for citation_id in analysis.citations)


def categorize_failures(
    case: EvalCase,
    retrieval_missing: list[str],
    answer_missing: list[str],
    forbidden_terms_found: list[str],
    citation_correct: Optional[bool],
    analysis: Optional[TriageAnalysisResponse],
) -> list[str]:
    failures = []

    if retrieval_missing:
        failures.append("retrieval_failure")

    if citation_correct is False:
        failures.append("citation_failure")

    if answer_missing or forbidden_terms_found:
        failures.append("answer_correctness_failure")

    if forbidden_terms_found:
        failures.append("grounding_failure")

    if analysis is not None:
        fallback_triggered = analysis.fallback_reason is not None
        if fallback_triggered != case.expected_fallback:
            failures.append("fallback_failure")

    return failures


def evaluate_case(
    case: EvalCase,
    top_k: int,
    run_analysis: bool,
) -> EvalCaseResult:
    incident = load_incident_bundle(case.incident_id)
    retrieved_chunks = retrieve_investigation_evidence(incident, top_k=top_k)
    retrieved_text = "\n".join(chunk.text for chunk in retrieved_chunks)
    retrieval_terms_found = find_matching_terms(
        case.expected_retrieval_terms,
        retrieved_text,
    )
    retrieval_terms_missing = find_missing_terms(
        case.expected_retrieval_terms,
        retrieved_text,
    )
    retrieval_score = (
        len(retrieval_terms_found) / len(case.expected_retrieval_terms)
        if case.expected_retrieval_terms
        else 1.0
    )

    analysis = (
        build_analysis_for_eval(incident=incident, top_k=top_k)
        if run_analysis
        else None
    )
    answer_text = (
        f"{analysis.summary}\n{analysis.hypothesis}"
        if analysis is not None
        else ""
    )
    answer_terms_found = (
        find_matching_terms(case.expected_answer_terms, answer_text)
        if analysis is not None
        else []
    )
    answer_terms_missing = (
        find_missing_terms(case.expected_answer_terms, answer_text)
        if analysis is not None
        else []
    )
    forbidden_terms_found = (
        find_matching_terms(case.forbidden_answer_terms, answer_text)
        if analysis is not None
        else []
    )
    citation_correct = (
        evaluate_citations(analysis)
        if analysis is not None
        else None
    )
    fallback_triggered = (
        analysis.fallback_reason is not None
        if analysis is not None
        else None
    )
    failure_categories = categorize_failures(
        case=case,
        retrieval_missing=retrieval_terms_missing,
        answer_missing=answer_terms_missing,
        forbidden_terms_found=forbidden_terms_found,
        citation_correct=citation_correct,
        analysis=analysis,
    )

    return EvalCaseResult(
        name=case.name,
        incident_id=case.incident_id,
        retrieval_score=round(retrieval_score, 3),
        retrieval_terms_found=retrieval_terms_found,
        retrieval_terms_missing=retrieval_terms_missing,
        citation_correct=citation_correct,
        answer_terms_found=answer_terms_found,
        answer_terms_missing=answer_terms_missing,
        forbidden_terms_found=forbidden_terms_found,
        fallback_triggered=fallback_triggered,
        failure_categories=failure_categories,
    )


def build_analysis_for_eval(
    incident,
    top_k: int,
) -> TriageAnalysisResponse:
    from app.triage_analysis import build_triage_analysis

    return build_triage_analysis(incident=incident, top_k=top_k)


def average(values: list[float]) -> Optional[float]:
    if not values:
        return None

    return round(mean(values), 3)


def build_eval_report(
    request: EvalRunRequest,
) -> EvalRunResponse:
    eval_cases = load_eval_cases()
    if request.incident_ids is not None:
        eval_cases = [
            case
            for case in eval_cases
            if case.incident_id in request.incident_ids
        ]

    results = [
        evaluate_case(
            case=case,
            top_k=request.top_k,
            run_analysis=request.run_analysis,
        )
        for case in eval_cases
    ]

    citation_scores = [
        1.0 if result.citation_correct else 0.0
        for result in results
        if result.citation_correct is not None
    ]
    fallback_scores = [
        1.0 if result.fallback_triggered else 0.0
        for result in results
        if result.fallback_triggered is not None
    ]
    answer_scores = [
        1.0 if not result.answer_terms_missing else 0.0
        for result in results
        if result.fallback_triggered is not None
    ]

    return EvalRunResponse(
        total_cases=len(results),
        retrieval_accuracy=average(
            [result.retrieval_score for result in results]
        ) or 0.0,
        citation_correctness=average(citation_scores),
        fallback_rate=average(fallback_scores),
        answer_match_rate=average(answer_scores),
        results=results,
    )
