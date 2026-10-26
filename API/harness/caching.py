from __future__ import annotations

from typing import Any


def build_system_with_cache(system_prompt: str, static_context: str) -> list[dict[str, Any]]:
    print("[harness/caching.py] build_system_with_cache")
    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": static_context,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def extract_cache_usage(usage: dict[str, Any]) -> dict[str, int]:
    print("[harness/caching.py] extract_cache_usage")
    return {
        "cache_read": int(usage.get("cache_read_input_tokens", 0) or 0),
        "cache_write": int(usage.get("cache_creation_input_tokens", 0) or 0),
    }
