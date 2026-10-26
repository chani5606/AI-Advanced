from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from harness.compaction import Compactor
from harness.context import ContextBuilder
from harness.history import HistoryStore
from harness.loop import AgentLoop
from harness.memory import MemoryManager
from harness.tools import ToolHarness


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_scenario(root: Path, scenario_path: Path) -> dict[str, Any]:
    client = OpenAI()
    scenario = load_scenario(scenario_path)

    run_root = root / "API" / "runtime"
    if run_root.exists():
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    history = HistoryStore(run_root / "history.json")
    memory_manager = MemoryManager(run_root)
    context_builder = ContextBuilder(memory_manager)
    compactor = Compactor(threshold=10)
    tool_harness = ToolHarness(run_root)
    loop = AgentLoop(client)

    turns_out: list[dict[str, Any]] = []

    for session in scenario["sessions"]:
        session_id = session["session_id"]
        user_id = session["user_id"]
        messages = history.load(session_id)

        for turn in session["turns"]:
            user_text = turn["user"]
            user_message = {"role": "user", "content": user_text}
            messages.append(user_message)
            history.append(session_id, user_message)

            compact_summary = compactor.maybe_compact(messages)
            context_blob = context_builder.build(user_id, user_text, compact_summary)
            result = loop.run_turn(
                messages=messages,
                tools=tool_harness.schemas(),
                context_blob=context_blob,
                tool_runner=tool_harness.dispatch,
            )
            messages = result["messages"]
            history.append(session_id, messages[-1])

            assistant_text = ""
            last_content = messages[-1]["content"]
            if isinstance(last_content, list):
                txt = [b["text"] for b in last_content if b.get("type") == "text"]
                assistant_text = "\n".join(txt)
            else:
                assistant_text = str(last_content)

            turns_out.append(
                {
                    "session_id": session_id,
                    "turn_id": turn["id"],
                    "user": user_text,
                    "assistant": assistant_text,
                    "tools_used": result["tools_used"],
                    "model_calls": result["model_calls"],
                    "usage": result["usage"],
                    "cost_usd": result["cost_usd"],
                    "latency_ms": result["latency_ms"],
                }
            )

    return {"turns": turns_out}


def evaluate_checks(result: dict[str, Any], scenario: dict[str, Any]) -> list[dict[str, Any]]:
    checks_out: list[dict[str, Any]] = []
    turns = result["turns"]
    root = Path(__file__).resolve().parents[1]
    mem_path = root / "API" / "runtime" / "state" / "memory.json"
    tasks_path = root / "API" / "runtime" / "state" / "tasks.json"
    mem_state = load_scenario(mem_path) if mem_path.exists() else {}
    tasks_state = load_scenario(tasks_path) if tasks_path.exists() else {}

    by_id = {(t["session_id"], t["turn_id"]): t for t in turns}
    for c in scenario["checks"]:
        t = by_id.get((c["session_id"], c["turn_id"]))
        passed = False
        reason = ""
        if t is None:
            reason = "turn not found"
        else:
            kind = c["type"]
            if kind == "tool_used":
                passed = c["tool"] in t["tools_used"]
            elif kind == "assistant_contains":
                passed = c["needle"].lower() in t["assistant"].lower()
            elif kind == "model_calls_at_least":
                passed = t["model_calls"] >= int(c["value"])
            elif kind == "state_pref_equals":
                uid = c["user_id"]
                k = c["key"]
                v = c["value"]
                passed = mem_state.get(uid, {}).get("preferences", {}).get(k) == v
            elif kind == "state_task_count_at_least":
                uid = c["user_id"]
                passed = len(tasks_state.get(uid, [])) >= int(c["value"])
            reason = "ok" if passed else "condition failed"

        checks_out.append({"id": c["id"], "passed": passed, "reason": reason})
    return checks_out


def count_loc(root: Path) -> dict[str, int]:
    files = [
        root / "API" / "harness" / "loop.py",
        root / "API" / "harness" / "tools.py",
        root / "API" / "harness" / "history.py",
        root / "API" / "harness" / "memory.py",
        root / "API" / "harness" / "context.py",
        root / "API" / "harness" / "compaction.py",
        root / "API" / "harness" / "caching.py",
        root / "API" / "harness" / "tokens.py",
    ]
    out: dict[str, int] = {}
    for p in files:
        with p.open("r", encoding="utf-8") as f:
            out[p.name] = sum(1 for _ in f)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    scenario_path = Path(args.scenario).resolve()

    run_result = run_scenario(root, scenario_path)
    scenario = load_scenario(scenario_path)
    checks = evaluate_checks(run_result, scenario)

    totals = {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_write": 0,
        "cost_usd": 0.0,
        "model_calls": 0,
        "latency_ms": 0,
    }
    for t in run_result["turns"]:
        totals["input"] += t["usage"]["input"]
        totals["output"] += t["usage"]["output"]
        totals["cache_read"] += t["usage"]["cache_read"]
        totals["cache_write"] += t["usage"]["cache_write"]
        totals["cost_usd"] += t["cost_usd"]
        totals["model_calls"] += t["model_calls"]
        totals["latency_ms"] += t["latency_ms"]

    payload = {
        "kind": "api",
        "turns": run_result["turns"],
        "checks": checks,
        "totals": totals,
        "harness_loc": count_loc(root),
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("[API/main.py] wrote", str(out_path))


if __name__ == "__main__":
    main()
