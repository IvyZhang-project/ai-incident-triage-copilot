from time import perf_counter
from typing import Optional
from uuid import uuid4

from app.models import TraceRecord, TriageAnalysisResponse


TRACE_STORE: dict[str, TraceRecord] = {}
PROMPT_VERSION = "deterministic-analysis-v1"
TOKEN_CHARS_PER_TOKEN = 4


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
    return round((input_tokens + output_tokens) * 0.0, 6)


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
    )
    TRACE_STORE[analysis.trace_id] = trace

    return trace


def get_trace(trace_id: str) -> Optional[TraceRecord]:
    return TRACE_STORE.get(trace_id)


def new_trace_id() -> str:
    return f"trace-{uuid4()}"
