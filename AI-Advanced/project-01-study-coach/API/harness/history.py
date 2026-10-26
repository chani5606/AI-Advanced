from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, session_id: str) -> list[dict[str, Any]]:
        print("[harness/history.py] load history", session_id)
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(session_id, [])

    def append(self, session_id: str, message: dict[str, Any]) -> None:
        print("[harness/history.py] append history", session_id)
        data: dict[str, Any]
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        data.setdefault(session_id, []).append(message)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
