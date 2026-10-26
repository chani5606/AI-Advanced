from __future__ import annotations

from typing import Any

from .memory import MemoryManager


class ContextBuilder:
    def __init__(self, memory_manager: MemoryManager) -> None:
        self.memory_manager = memory_manager

    def build(self, user_id: str, user_text: str, compact_summary: str | None) -> dict[str, Any]:
        print("[harness/context.py] build context")
        keys = []
        if "בוקר" in user_text or "morning" in user_text.lower():
            keys.append("study_time")
        if "קצר" in user_text or "brief" in user_text.lower():
            keys.append("answer_style")

        mem = self.memory_manager.get_relevant(user_id, keys if keys else None)
        return {
            "memory": mem,
            "summary": compact_summary,
            "user_focus": user_text[:120],
        }
