from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class FakeUsage:
    prompt_tokens: int = 120
    completion_tokens: int = 60


@dataclass
class FakeToolFunction:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeToolFunction


@dataclass
class FakeMessage:
    content: str | None
    tool_calls: list[FakeToolCall] | None = None


@dataclass
class FakeChoice:
    message: FakeMessage


class FakeResponse:
    def __init__(self, message: FakeMessage, usage: FakeUsage) -> None:
        self.choices = [FakeChoice(message=message)]
        self.usage = usage


class _ChatCompletions:
    def __init__(self) -> None:
        self._tool_counter = 0

    def create(self, **kwargs: Any) -> FakeResponse:
        messages = kwargs.get("messages", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        last_user = user_msgs[-1]["content"] if user_msgs else ""

        if isinstance(last_user, str):
            text = last_user
            if "תשמרי" in text:
                self._tool_counter += 1
                tc = FakeToolCall(
                    id=f"tc_{self._tool_counter}",
                    function=FakeToolFunction(
                        name="save_preference",
                        arguments=json.dumps({"user_id": "hani", "key": "answer_style", "value": "short"}),
                    ),
                )
                return FakeResponse(FakeMessage(content="", tool_calls=[tc]), FakeUsage())

        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        if tool_msgs:
            return FakeResponse(
                FakeMessage(content="בוצע. אם יש סתירה אציין שהיא סותרת העדפה קודמת.", tool_calls=None),
                FakeUsage(),
            )

        return FakeResponse(FakeMessage(content="סיכום קצר הוכן.", tool_calls=None), FakeUsage())


class _Chat:
    def __init__(self) -> None:
        self.completions = _ChatCompletions()


class FakeOpenAI:
    def __init__(self) -> None:
        self.chat = _Chat()
