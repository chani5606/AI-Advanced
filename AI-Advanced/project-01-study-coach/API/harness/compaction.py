from __future__ import annotations

from typing import Any


class Compactor:
    def __init__(self, threshold: int = 10) -> None:
        self.threshold = threshold

    def maybe_compact(self, messages: list[dict[str, Any]]) -> str | None:
        print("[harness/compaction.py] maybe_compact")
        if len(messages) <= self.threshold:
            return None
        tail = messages[-6:]
        parts: list[str] = []
        for m in tail:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, list):
                parts.append(f"{role}: blocks={len(content)}")
            else:
                parts.append(f"{role}: {str(content)[:120]}")
        return " | ".join(parts)
