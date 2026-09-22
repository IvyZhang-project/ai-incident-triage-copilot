from app.incident_analysis import build_baseline_triage
from app.incident_loader import load_incident_bundle


def test_conflicting_evidence_reduces_consistency_and_quality() -> None:
    incident = load_incident_bundle("conflicting_evidence_case")

    result = build_baseline_triage(incident)

    assert result.evidence_quality.signal_strength == "strong"
    assert result.evidence_quality.consistency == "weak"
    assert result.evidence_quality.level == "medium"
    assert result.investigation_risk == "medium"


def test_missing_metrics_are_reported_as_a_data_gap() -> None:
    incident = load_incident_bundle("missing_metrics_case")

    result = build_baseline_triage(incident)

    assert result.evidence_quality.coverage.has_metrics is False
    assert result.evidence_quality.data_gaps == ["metrics"]
    assert result.evidence_quality.level == "medium"
