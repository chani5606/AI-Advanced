from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.domain_tools import DomainStore


class MemoryManager:
    def __init__(self, root: Path) -> None:
        self.store = DomainStore(root)

    def get_relevant(self, user_id: str, keys: list[str] | None = None) -> dict[str, Any]:
        print("[harness/memory.py] get_relevant", user_id)
        mem = self.store.load_memory(user_id)
        if not keys:
            return {
                "preferences": mem.preferences,
                "recent_decisions": mem.decisions[-5:],
                "recent_history": mem.task_history[-3:],
            }
        return {
            "preferences": {k: mem.preferences.get(k) for k in keys},
            "recent_decisions": mem.decisions[-5:],
        }
