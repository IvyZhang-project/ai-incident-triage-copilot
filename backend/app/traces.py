import os
from time import perf_counter
from typing import Optional
from uuid import uuid4

from app.models import TraceRecord, TriageAnalysisResponse


TRACE_STORE: dict[str, TraceRecord] = {}
PROMPT_VERSION = "llm-ready-analysis-v1"
TOKEN_CHARS_PER_TOKEN = 4
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
TOKEN_PRICES_PER_1M = {
    "gpt-4.1-mini": {
        "input": 0.40,
        "output": 1.60,
    },
    "gpt-4.1": {
        "input": 2.00,
        "output": 8.00,
    },
    "gpt-4.1-nano": {
        "input": 0.10,
        "output": 0.40,
    },
}


def start_timer() -> float:
    return perf_counter()


def calculate_latency_ms(start_time: float) -> int:
    return int((perf_counter() - start_time) * 1000)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0

    return max(1, len(text) // TOKEN_CHARS_PER_TOKEN)


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
) -> float:
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    prices = TOKEN_PRICES_PER_1M.get(
        model,
        TOKEN_PRICES_PER_1M[DEFAULT_OPENAI_MODEL],
    )
    input_cost = input_tokens / 1_000_000 * prices["input"]
    output_cost = output_tokens / 1_000_000 * prices["output"]

    return round(input_cost + output_cost, 6)


def save_trace(
    incident_id: str,
    input_source: str,
    prompt: str,
    analysis: TriageAnalysisResponse,
    latency_ms: int,
    query: Optional[dict[str, str]] = None,
) -> TraceRecord:
    input_tokens = estimate_tokens(prompt)
    output_tokens = estimate_tokens(analysis.model_dump_json())

    trace = TraceRecord(
        trace_id=analysis.trace_id,
        incident_id=incident_id,
        input_source=input_source,
        query=query,
        retrieved_chunk_ids=analysis.retrieved_chunk_ids,
        prompt_version=PROMPT_VERSION,
        prompt=prompt,
        model_output=analysis,
        latency_ms=latency_ms,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_cost_usd=estimate_cost_usd(input_tokens, output_tokens),
        fallback_reason=analysis.fallback_reason,
        llm_failure_code=analysis.llm_failure_code,
    )
    TRACE_STORE[analysis.trace_id] = trace

    return trace


def get_trace(trace_id: str) -> Optional[TraceRecord]:
    return TRACE_STORE.get(trace_id)


def new_trace_id() -> str:
    return f"trace-{uuid4()}"
