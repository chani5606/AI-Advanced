from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StudyTask:
    course: str
    topic: str
    deadline: str
    priority: int
    done: bool = False


@dataclass
class UserMemory:
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)
    task_history: list[dict[str, Any]] = field(default_factory=list)
