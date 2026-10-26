from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.domain_tools import DomainStore, DomainTools


class ToolHarness:
    def __init__(self, root: Path) -> None:
        self.tools = DomainTools(DomainStore(root))

    def schemas(self) -> list[dict[str, Any]]:
        print("[harness/tools.py] schemas")
        return [
            {
                "name": "add_task",
                "description": "Add a study task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "course": {"type": "string"},
                        "topic": {"type": "string"},
                        "deadline": {"type": "string"},
                        "priority": {"type": "integer"},
                    },
                    "required": ["user_id", "course", "topic", "deadline", "priority"],
                },
            },
            {
                "name": "list_tasks",
                "description": "List study tasks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "course": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            },
            {
                "name": "save_preference",
                "description": "Save user preference",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["user_id", "key", "value"],
                },
            },
            {
                "name": "recall_memory",
                "description": "Recall memory/preferences",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "key": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            },
            {
                "name": "get_course_hints_external",
                "description": "Fetch external hints by course",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "course": {"type": "string"},
                    },
                    "required": ["course"],
                },
            },
        ]

    def dispatch(self, name: str, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        print("[harness/tools.py] dispatch", name)
        try:
            if name == "add_task":
                res = self.tools.add_task(**payload)
            elif name == "list_tasks":
                res = self.tools.list_tasks(**payload)
            elif name == "save_preference":
                res = self.tools.save_preference(**payload)
            elif name == "recall_memory":
                res = self.tools.recall_memory(**payload)
            elif name == "get_course_hints_external":
                res = self.tools.get_course_hints_external(**payload)
            else:
                return ({"error": f"Unknown tool: {name}"}, True)
            return (res, False)
        except Exception as e:  # Keep errors model-visible as tool_result is_error.
            return ({"error": str(e), "tool": name}, True)
