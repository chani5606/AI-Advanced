from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent import EFFORT, MAX_TOKENS, MODEL, SYSTEM_PROMPT
import tools as sdk_tools
from shared.storage import read_json, write_json

# replaces: harness/history.py
HISTORY_PATH = Path(__file__).resolve().parents[1] / "SDK" / "runtime" / "history.json"


# replaces: harness/caching.py
# replaces: harness/context.py
# replaces: harness/compaction.py
# replaces: harness/loop.py
# replaces: harness/memory.py
# replaces: harness/tokens.py
# NOTE: In a real Claude Agent SDK run, these parts are managed by SDK runtime.
# Here we keep a compact emulation that marks what SDK would replace.

STRICT_MCP_CONFIG = True
ALLOWED_TOOLS = [
    "add_task",
    "list_tasks",
    "save_preference",
    "recall_memory",
    "get_course_hints_external",
]

TOOL_MAP = {
    "add_task": sdk_tools.add_task,
    "list_tasks": sdk_tools.list_tasks,
    "save_preference": sdk_tools.save_preference,
    "recall_memory": sdk_tools.recall_memory,
    "get_course_hints_external": sdk_tools.get_course_hints_external,
}


def load_history(session_id: str) -> list[dict[str, Any]]:
    data = read_json(HISTORY_PATH, {})
    return data.get(session_id, [])


def append_history(session_id: str, message: dict[str, Any]) -> None:
    data = read_json(HISTORY_PATH, {})
    data.setdefault(session_id, []).append(message)
    write_json(HISTORY_PATH, data)


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def usage_to_dict(raw_usage: Any) -> dict[str, int]:
    if raw_usage is None:
        return {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    return {
        "input": int(getattr(raw_usage, "input_tokens", getattr(raw_usage, "prompt_tokens", 0)) or 0),
        "output": int(getattr(raw_usage, "output_tokens", getattr(raw_usage, "completion_tokens", 0)) or 0),
        "cache_read": int(getattr(raw_usage, "cache_read_input_tokens", 0) or 0),
        "cache_write": int(getattr(raw_usage, "cache_creation_input_tokens", 0) or 0),
    }


def estimate_cost(u: dict[str, int]) -> float:
    return round(
        (u["input"] / 1_000_000) * 15.0
        + (u["output"] / 1_000_000) * 75.0
        + (u["cache_read"] / 1_000_000) * 1.5
        + (u["cache_write"] / 1_000_000) * 18.0,
        6,
    )


def run_turn(client: OpenAI, messages: list[dict[str, Any]]) -> dict[str, Any]:
    calls = 0
    tools_used: list[str] = []
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    start = time.perf_counter()

    tools = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"SDK tool {name}",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
            },
        }
        for name in ALLOWED_TOOLS
    ]

    system_text = f"{SYSTEM_PROMPT}\n\nstrict_mcp_config={STRICT_MCP_CONFIG}; effort={EFFORT}"
    oa_messages: list[dict[str, Any]] = [{"role": "system", "content": system_text}]

    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            oa_messages.append({"role": "user", "content": m["content"]})
        elif m.get("role") == "assistant":
            blocks = m.get("content")
            if isinstance(blocks, list):
                text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
                tool_parts = [b for b in blocks if b.get("type") == "tool_use"]
                if text_parts:
                    oa_messages.append({"role": "assistant", "content": "\n".join(text_parts)})
                if tool_parts:
                    oa_messages.append(
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": p["id"],
                                    "type": "function",
                                    "function": {
                                        "name": p["name"],
                                        "arguments": json.dumps(p["input"], ensure_ascii=False),
                                    },
                                }
                                for p in tool_parts
                            ],
                        }
                    )
        elif m.get("role") == "user" and isinstance(m.get("content"), list):
            for tr in m["content"]:
                if tr.get("type") == "tool_result":
                    txt = ""
                    c = tr.get("content", [])
                    if c and isinstance(c, list):
                        txt = c[0].get("text", "")
                    oa_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tr.get("tool_use_id"),
                            "content": txt,
                        }
                    )

    while True:
        calls += 1
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=oa_messages,
            tools=tools,
            tool_choice="auto",
        )
        u = usage_to_dict(resp.usage)
        for k in usage:
            usage[k] += u[k]

        assistant_blocks: list[dict[str, Any]] = []
        msg = resp.choices[0].message
        if msg.content:
            assistant_blocks.append({"type": "text", "text": msg.content})
        tool_calls = msg.tool_calls or []
        for tc in tool_calls:
            payload = json.loads(tc.function.arguments or "{}")
            assistant_blocks.append(
                {"type": "tool_use", "id": tc.id, "name": tc.function.name, "input": payload}
            )

        messages.append({"role": "assistant", "content": assistant_blocks})

        oa_assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": msg.content or "",
        }
        if tool_calls:
            oa_assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in tool_calls
            ]
        oa_messages.append(oa_assistant_msg)

        if not tool_calls:
            break

        tool_results: list[dict[str, Any]] = []
        tool_result_user_content: list[dict[str, Any]] = []
        for b in assistant_blocks:
            if b["type"] != "tool_use":
                continue
            name = b["name"]
            payload = b["input"]
            if STRICT_MCP_CONFIG and name not in TOOL_MAP:
                out = {"error": f"tool not allowed: {name}"}
                is_error = True
            else:
                try:
                    out = TOOL_MAP[name](**payload)
                    is_error = False
                except Exception as e:
                    out = {"error": str(e), "tool": name}
                    is_error = True
            tools_used.append(name)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": b["id"],
                    "is_error": is_error,
                    "content": [{"type": "text", "text": str(out)}],
                }
            )
            tool_result_user_content.append(
                {
                    "role": "tool",
                    "tool_call_id": b["id"],
                    "content": str(out),
                }
            )

        messages.append({"role": "user", "content": tool_results})
        oa_messages.extend(tool_result_user_content)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "messages": messages,
        "tools_used": tools_used,
        "model_calls": calls,
        "usage": usage,
        "cost_usd": estimate_cost(usage),
        "latency_ms": latency_ms,
    }


def evaluate_checks(result: dict[str, Any], scenario: dict[str, Any]) -> list[dict[str, Any]]:
    checks_out: list[dict[str, Any]] = []
    turns = result["turns"]
    root = Path(__file__).resolve().parents[1]
    mem_path = root / "SDK" / "runtime" / "state" / "memory.json"
    tasks_path = root / "SDK" / "runtime" / "state" / "tasks.json"
    mem_state = load_scenario(mem_path) if mem_path.exists() else {}
    tasks_state = load_scenario(tasks_path) if tasks_path.exists() else {}
    by_id = {(t["session_id"], t["turn_id"]): t for t in turns}
    for c in scenario["checks"]:
        t = by_id.get((c["session_id"], c["turn_id"]))
        passed = False
        if t is not None:
            if c["type"] == "tool_used":
                passed = c["tool"] in t["tools_used"]
            elif c["type"] == "assistant_contains":
                passed = c["needle"].lower() in t["assistant"].lower()
            elif c["type"] == "model_calls_at_least":
                passed = t["model_calls"] >= int(c["value"])
            elif c["type"] == "state_pref_equals":
                uid = c["user_id"]
                k = c["key"]
                v = c["value"]
                passed = mem_state.get(uid, {}).get("preferences", {}).get(k) == v
            elif c["type"] == "state_task_count_at_least":
                uid = c["user_id"]
                passed = len(tasks_state.get(uid, [])) >= int(c["value"])
        checks_out.append({"id": c["id"], "passed": passed, "reason": "ok" if passed else "condition failed"})
    return checks_out


def count_sdk_loc(root: Path) -> dict[str, int]:
    files = [root / "SDK" / "main.py", root / "SDK" / "tools.py", root / "SDK" / "agent.py"]
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
    run_root = root / "SDK" / "runtime"
    if run_root.exists():
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    scenario_path = Path(args.scenario).resolve()
    scenario = load_scenario(scenario_path)

    client = OpenAI()
    turns_out: list[dict[str, Any]] = []

    for session in scenario["sessions"]:
        session_id = session["session_id"]
        messages = load_history(session_id)

        for turn in session["turns"]:
            user_text = turn["user"]
            user_msg = {"role": "user", "content": user_text}
            messages.append(user_msg)
            append_history(session_id, user_msg)

            result = run_turn(client, messages)
            messages = result["messages"]
            append_history(session_id, messages[-1])

            assistant_text = ""
            last_content = messages[-1]["content"]
            if isinstance(last_content, list):
                assistant_text = "\n".join([b["text"] for b in last_content if b.get("type") == "text"])
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

    checks = evaluate_checks({"turns": turns_out}, scenario)

    totals = {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_write": 0,
        "cost_usd": 0.0,
        "model_calls": 0,
        "latency_ms": 0,
    }
    for t in turns_out:
        totals["input"] += t["usage"]["input"]
        totals["output"] += t["usage"]["output"]
        totals["cache_read"] += t["usage"]["cache_read"]
        totals["cache_write"] += t["usage"]["cache_write"]
        totals["cost_usd"] += t["cost_usd"]
        totals["model_calls"] += t["model_calls"]
        totals["latency_ms"] += t["latency_ms"]

    out = {
        "kind": "sdk",
        "strict_mcp_config": STRICT_MCP_CONFIG,
        "allowed_tools": ALLOWED_TOOLS,
        "turns": turns_out,
        "checks": checks,
        "totals": totals,
        "harness_loc": count_sdk_loc(root),
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("[SDK/main.py] wrote", str(out_path))


if __name__ == "__main__":
    main()
