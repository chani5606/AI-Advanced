from __future__ import annotations

from typing import Any

# Rough pricing placeholders, can be changed from env if needed.
PRICE_INPUT_PER_MTOK = 15.0
PRICE_OUTPUT_PER_MTOK = 75.0
PRICE_CACHE_READ_PER_MTOK = 1.5
PRICE_CACHE_WRITE_PER_MTOK = 18.0


def to_usage_dict(raw_usage: Any) -> dict[str, int]:
    print("[harness/tokens.py] to_usage_dict")
    if raw_usage is None:
        return {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    if isinstance(raw_usage, dict):
        src = raw_usage
    else:
        src = {
            "input_tokens": getattr(raw_usage, "input_tokens", getattr(raw_usage, "prompt_tokens", 0)),
            "output_tokens": getattr(raw_usage, "output_tokens", getattr(raw_usage, "completion_tokens", 0)),
            "cache_read_input_tokens": getattr(raw_usage, "cache_read_input_tokens", 0),
            "cache_creation_input_tokens": getattr(raw_usage, "cache_creation_input_tokens", 0),
        }
    return {
        "input": int(src.get("input_tokens", 0) or 0),
        "output": int(src.get("output_tokens", 0) or 0),
        "cache_read": int(src.get("cache_read_input_tokens", 0) or 0),
        "cache_write": int(src.get("cache_creation_input_tokens", 0) or 0),
    }


def estimate_cost_usd(u: dict[str, int]) -> float:
    print("[harness/tokens.py] estimate_cost_usd")
    cost = 0.0
    cost += (u["input"] / 1_000_000) * PRICE_INPUT_PER_MTOK
    cost += (u["output"] / 1_000_000) * PRICE_OUTPUT_PER_MTOK
    cost += (u["cache_read"] / 1_000_000) * PRICE_CACHE_READ_PER_MTOK
    cost += (u["cache_write"] / 1_000_000) * PRICE_CACHE_WRITE_PER_MTOK
    return round(cost, 6)
