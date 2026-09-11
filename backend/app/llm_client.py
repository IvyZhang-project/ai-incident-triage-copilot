import json
import os
from typing import Optional

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.models import LLMAnalysisOutput


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
REQUEST_TIMEOUT_SECONDS = 20


class LLMGenerationError(Exception):
    """Raised when the configured LLM call cannot produce valid output."""


def is_llm_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


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
        raise LLMGenerationError("LLM response was not valid JSON.") from exc

    try:
        return LLMAnalysisOutput.model_validate(payload)
    except ValidationError as exc:
        raise LLMGenerationError("LLM response did not match the schema.") from exc


def extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    raise LLMGenerationError("OpenAI response did not include output text.")


def call_openai_analysis(prompt: str) -> LLMAnalysisOutput:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMGenerationError("OPENAI_API_KEY is not configured.")

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
        raise LLMGenerationError("OpenAI request failed.") from exc

    return parse_llm_analysis_output(extract_response_text(response))


def generate_llm_analysis(prompt: str) -> Optional[LLMAnalysisOutput]:
    if not is_llm_configured():
        return None

    try:
        return call_openai_analysis(prompt)
    except LLMGenerationError:
        return None
