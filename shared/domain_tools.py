from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .external_data import COURSE_HINTS
from .models import StudyTask, UserMemory
from .storage import read_json, write_json


class DomainStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.memory_path = root / "state" / "memory.json"
        self.tasks_path = root / "state" / "tasks.json"

    def load_memory(self, user_id: str) -> UserMemory:
        data = read_json(self.memory_path, {})
        row = data.get(user_id)
        if row is None:
            return UserMemory(user_id=user_id)
        return UserMemory(
            user_id=user_id,
            preferences=row.get("preferences", {}),
            decisions=row.get("decisions", []),
            task_history=row.get("task_history", []),
        )

    def save_memory(self, mem: UserMemory) -> None:
        data = read_json(self.memory_path, {})
        data[mem.user_id] = asdict(mem)
        write_json(self.memory_path, data)

    def load_tasks(self, user_id: str) -> list[StudyTask]:
        data = read_json(self.tasks_path, {})
        rows = data.get(user_id, [])
        return [StudyTask(**r) for r in rows]

    def save_tasks(self, user_id: str, tasks: list[StudyTask]) -> None:
        data = read_json(self.tasks_path, {})
        data[user_id] = [asdict(t) for t in tasks]
        write_json(self.tasks_path, data)


class DomainTools:
    def __init__(self, store: DomainStore) -> None:
        self.store = store

    def add_task(
        self,
        user_id: str,
        course: str,
        topic: str,
        deadline: str,
        priority: int,
    ) -> dict[str, Any]:
        tasks = self.store.load_tasks(user_id)
        new_task = StudyTask(
            course=course,
            topic=topic,
            deadline=deadline,
            priority=priority,
            done=False,
        )
        tasks.append(new_task)
        self.store.save_tasks(user_id, tasks)

        mem = self.store.load_memory(user_id)
        mem.task_history.append(
            {
                "event": "add_task",
                "course": course,
                "topic": topic,
                "deadline": deadline,
            }
        )
        self.store.save_memory(mem)
        return {
            "ok": True,
            "task_count": len(tasks),
            "task": {
                "course": course,
                "topic": topic,
                "deadline": deadline,
                "priority": priority,
            },
        }

    def list_tasks(self, user_id: str, course: str | None = None) -> dict[str, Any]:
        tasks = self.store.load_tasks(user_id)
        if course:
            tasks = [t for t in tasks if t.course.lower() == course.lower()]
        compact = [
            {
                "course": t.course,
                "topic": t.topic,
                "deadline": t.deadline,
                "p": t.priority,
                "d": int(t.done),
            }
            for t in tasks
        ]
        return {"ok": True, "tasks": compact, "count": len(compact)}

    def save_preference(self, user_id: str, key: str, value: str) -> dict[str, Any]:
        mem = self.store.load_memory(user_id)
        mem.preferences[key] = value
        mem.decisions.append(f"pref:{key}={value}")
        self.store.save_memory(mem)
        return {"ok": True, "saved": {key: value}, "decision_count": len(mem.decisions)}

    def recall_memory(self, user_id: str, key: str | None = None) -> dict[str, Any]:
        mem = self.store.load_memory(user_id)
        if key:
            return {
                "ok": True,
                "value": mem.preferences.get(key),
                "decisions": mem.decisions[-5:],
            }
        return {
            "ok": True,
            "preferences": mem.preferences,
            "decisions": mem.decisions[-10:],
            "history_tail": mem.task_history[-5:],
        }

    def get_course_hints_external(self, course: str) -> dict[str, Any]:
        hints = COURSE_HINTS.get(course.lower(), ["No hints found for this course."])
        return {
            "ok": True,
            "course": course,
            "hints": hints[:3],
            "source": "shared.external_data.COURSE_HINTS",
        }
