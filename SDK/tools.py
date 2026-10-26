from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.domain_tools import DomainStore, DomainTools

ROOT = Path(__file__).resolve().parents[1] / "SDK" / "runtime"
ROOT.mkdir(parents=True, exist_ok=True)
TOOLS = DomainTools(DomainStore(ROOT))


# replaces: harness/tools.py

def add_task(user_id: str, course: str, topic: str, deadline: str, priority: int) -> dict[str, Any]:
    return TOOLS.add_task(user_id=user_id, course=course, topic=topic, deadline=deadline, priority=priority)


# replaces: harness/tools.py

def list_tasks(user_id: str, course: str | None = None) -> dict[str, Any]:
    return TOOLS.list_tasks(user_id=user_id, course=course)


# replaces: harness/tools.py

def save_preference(user_id: str, key: str, value: str) -> dict[str, Any]:
    return TOOLS.save_preference(user_id=user_id, key=key, value=value)


# replaces: harness/tools.py

def recall_memory(user_id: str, key: str | None = None) -> dict[str, Any]:
    return TOOLS.recall_memory(user_id=user_id, key=key)


# replaces: harness/tools.py

def get_course_hints_external(course: str) -> dict[str, Any]:
    return TOOLS.get_course_hints_external(course=course)
