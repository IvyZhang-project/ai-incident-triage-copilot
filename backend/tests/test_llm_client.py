import pytest

from app.llm_client import (
    LLMGenerationError,
    classify_openai_error,
    parse_llm_analysis_output,
)


def test_invalid_json_has_structured_failure_code() -> None:
    with pytest.raises(LLMGenerationError) as exc_info:
        parse_llm_analysis_output("not-json")

    assert exc_info.value.code == "invalid_json"


def test_schema_mismatch_has_structured_failure_code() -> None:
    with pytest.raises(LLMGenerationError) as exc_info:
        parse_llm_analysis_output('{"summary": "missing fields"}')

    assert exc_info.value.code == "schema_validation_error"


def test_provider_error_is_mapped_to_application_error_code() -> None:
    rate_limit_error = type("RateLimitError", (Exception,), {})()

    assert classify_openai_error(rate_limit_error) == "rate_limit_error"


def test_unknown_provider_error_uses_safe_default() -> None:
    unknown_error = type("NewProviderError", (Exception,), {})()

    assert classify_openai_error(unknown_error) == "api_request_error"
