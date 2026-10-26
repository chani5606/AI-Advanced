from __future__ import annotations

from pathlib import Path

from API.harness.compaction import Compactor
from API.harness.context import ContextBuilder
from API.harness.loop import AgentLoop
from API.harness.memory import MemoryManager
from API.harness.tools import ToolHarness
from tests.fake_client import FakeOpenAI


def test_offline_agent_flow() -> None:
    root = Path(__file__).resolve().parents[1] / "tests" / "runtime"
    root.mkdir(parents=True, exist_ok=True)

    client = FakeOpenAI()
    loop = AgentLoop(client=client)  # type: ignore[arg-type]
    tools = ToolHarness(root)
    memory = MemoryManager(root)
    context = ContextBuilder(memory)
    compactor = Compactor(3)

    messages = [{"role": "user", "content": "תשמרי שאני מעדיפה קצר"}]
    result = loop.run_turn(
        messages=messages,
        tools=tools.schemas(),
        context_blob=context.build("hani", "תשמרי שאני מעדיפה קצר", compactor.maybe_compact(messages)),
        tool_runner=tools.dispatch,
    )

    assert result["model_calls"] >= 2
    assert "save_preference" in result["tools_used"]
