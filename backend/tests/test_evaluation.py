from app.evaluation import build_eval_report, term_matches_text
from app.models import EvalRunRequest


def test_term_matching_normalizes_service_name_separators() -> None:
    assert term_matches_text("inventory-api", "Inventory API timed out")
    assert term_matches_text("checkout_api", "Checkout API is healthy")


def test_retrieval_only_eval_passes_all_golden_cases() -> None:
    report = build_eval_report(
        EvalRunRequest(run_analysis=False, top_k=10)
    )

    assert report.total_cases == 6
    assert report.retrieval_accuracy == 1.0
    assert all(not result.failure_categories for result in report.results)
    assert report.citation_correctness is None
    assert report.answer_match_rate is None
