import argparse
from pathlib import Path
from typing import Optional

from app.env_loader import load_dotenv
from app.evaluation import build_eval_report
from app.incident_loader import PROJECT_ROOT
from app.models import EvalCaseResult, EvalRunRequest, EvalRunResponse


RETRIEVAL_REPORT_PATH = PROJECT_ROOT / "reports" / "retrieval-eval-report.md"
FULL_ANALYSIS_REPORT_PATH = (
    PROJECT_ROOT / "reports" / "full-analysis-eval-report.md"
)


def format_metric(value: Optional[float]) -> str:
    if value is None:
        return "Not run"

    return f"{value:.1%}"


def format_case_status(result: EvalCaseResult) -> str:
    if not result.failure_categories:
        return "Pass"

    return ", ".join(result.failure_categories)


def format_optional_bool(value: Optional[bool]) -> str:
    if value is None:
        return "Not run"

    return "Yes" if value else "No"


def render_eval_report(
    report: EvalRunResponse,
    request: EvalRunRequest,
) -> str:
    mode = "Full analysis" if request.run_analysis else "Retrieval only"
    lines = [
        "# Evaluation Report",
        "",
        "## Run Configuration",
        "",
        f"- Mode: {mode}",
        f"- Top-K: {request.top_k}",
        f"- Cases: {report.total_cases}",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Retrieval accuracy | {format_metric(report.retrieval_accuracy)} |",
        f"| Citation correctness | {format_metric(report.citation_correctness)} |",
        f"| Answer match rate | {format_metric(report.answer_match_rate)} |",
        f"| Fallback rate | {format_metric(report.fallback_rate)} |",
        "",
        "## Case Results",
        "",
        "| Incident | Retrieval | Citations valid | Fallback | Status |",
        "| --- | ---: | --- | --- | --- |",
    ]

    for result in report.results:
        lines.append(
            "| "
            f"`{result.incident_id}` | "
            f"{format_metric(result.retrieval_score)} | "
            f"{format_optional_bool(result.citation_correct)} | "
            f"{format_optional_bool(result.fallback_triggered)} | "
            f"{format_case_status(result)} |"
        )

    failures = [
        result
        for result in report.results
        if result.failure_categories
    ]
    lines.extend(
        [
            "",
            "## Failure Details",
            "",
        ]
    )

    if not failures:
        lines.append("No evaluation failures were detected in this run.")
    else:
        for result in failures:
            lines.extend(
                [
                    f"### `{result.incident_id}`",
                    "",
                    "- Categories: " + ", ".join(result.failure_categories),
                    "- Missing retrieval terms: "
                    + (", ".join(result.retrieval_terms_missing) or "None"),
                    "- Missing answer terms: "
                    + (", ".join(result.answer_terms_missing) or "None"),
                    "- Forbidden terms found: "
                    + (", ".join(result.forbidden_terms_found) or "None"),
                    "",
                ]
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Retrieval-only mode evaluates whether the ranking layer returns "
            "the expected evidence without calling an LLM. Full-analysis mode "
            "also evaluates citation validity, expected answer concepts, "
            "forbidden claims, and fallback behavior.",
            "",
            "This golden set uses synthetic incidents with known expectations. "
            "It measures regression behavior for these cases; it does not prove "
            "correctness for every unknown production incident.",
            "",
            "Full-analysis metrics describe one model run per case. Because LLM "
            "output is nondeterministic, repeated-run pass rates are a future "
            "stability improvement.",
            "",
        ]
    )

    return "\n".join(lines)


def write_eval_report(
    request: EvalRunRequest,
    output_path: Optional[Path] = None,
) -> Path:
    if request.run_analysis:
        load_dotenv()

    if output_path is None:
        output_path = (
            FULL_ANALYSIS_REPORT_PATH
            if request.run_analysis
            else RETRIEVAL_REPORT_PATH
        )

    report = build_eval_report(request)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_eval_report(report, request))
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a persistent Markdown evaluation report.",
    )
    parser.add_argument(
        "--run-analysis",
        action="store_true",
        help="Call the configured LLM and evaluate full analysis output.",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = EvalRunRequest(
        top_k=args.top_k,
        run_analysis=args.run_analysis,
    )
    output_path = write_eval_report(request, args.output)
    print(f"Evaluation report written to {output_path}")


if __name__ == "__main__":
    main()
