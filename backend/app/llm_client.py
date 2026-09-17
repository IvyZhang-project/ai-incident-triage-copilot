import json
import os

from pydantic import ValidationError

from app.models import LLMAnalysisOutput, LLMGenerationResult

try:
    from openai import OpenAI, OpenAIError
except ImportError:
    OpenAI = None
    OpenAIError = Exception


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
REQUEST_TIMEOUT_SECONDS = 20


class LLMGenerationError(Exception):
    """Raised when the configured LLM call cannot produce valid output."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def strip_markdown_code_fence(text: str) -> str:
    cleaned = text.strip()

    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()


def parse_llm_analysis_output(text: str) -> LLMAnalysisOutput:
    try:
        payload = json.loads(strip_markdown_code_fence(text))
    except json.JSONDecodeError as exc:
        raise LLMGenerationError(
            "invalid_json",
            "LLM response was not valid JSON.",
        ) from exc

    try:
        return LLMAnalysisOutput.model_validate(payload)
    except ValidationError as exc:
        raise LLMGenerationError(
            "schema_validation_error",
            "LLM response did not match the required schema.",
        ) from exc


def extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    raise LLMGenerationError(
        "empty_response",
        "OpenAI response did not include output text.",
    )


def classify_openai_error(error: Exception) -> str:
    error_name = type(error).__name__
    error_codes = {
        "APIConnectionError": "api_connection_error",
        "APITimeoutError": "api_timeout",
        "AuthenticationError": "authentication_error",
        "BadRequestError": "bad_request_error",
        "RateLimitError": "rate_limit_error",
    }

    return error_codes.get(error_name, "api_request_error")


def call_openai_analysis(prompt: str) -> LLMAnalysisOutput:
    if OpenAI is None:
        raise LLMGenerationError(
            "sdk_not_installed",
            "OpenAI SDK is not installed.",
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMGenerationError(
            "missing_api_key",
            "OPENAI_API_KEY is not configured.",
        )

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    client = OpenAI(
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )
    except OpenAIError as exc:
        failure_code = classify_openai_error(exc)
        raise LLMGenerationError(
            failure_code,
            f"OpenAI request failed with {type(exc).__name__}.",
        ) from exc

    return parse_llm_analysis_output(extract_response_text(response))


def generate_llm_analysis(prompt: str) -> LLMGenerationResult:
    try:
        return LLMGenerationResult(output=call_openai_analysis(prompt))
    except LLMGenerationError as exc:
        return LLMGenerationResult(
            failure_code=exc.code,
            failure_message=str(exc),
        )
