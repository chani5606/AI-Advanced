from __future__ import annotations

import json
import time
from typing import Any

from openai import OpenAI

from API.agent import EFFORT, MAX_TOKENS, MODEL, SYSTEM_PROMPT
from .tokens import estimate_cost_usd, to_usage_dict


class AgentLoop:
    def __init__(self, client: OpenAI) -> None:
        self.client = client

    def run_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        context_blob: dict[str, Any],
        tool_runner,
    ) -> dict[str, Any]:
        print("[harness/loop.py] run_turn")
        calls = 0
        used_tools: list[str] = []
        start = time.perf_counter()
        turn_usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}

        system_text = f"{SYSTEM_PROMPT}\n\neffort={EFFORT}; context={context_blob}"

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

        oa_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

        while True:
            calls += 1
            resp = self.client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=oa_messages,
                tools=oa_tools,
                tool_choice="auto",
            )

            usage = to_usage_dict(resp.usage)
            for k in turn_usage:
                turn_usage[k] += usage[k]

            assistant_blocks: list[dict[str, Any]] = []
            msg = resp.choices[0].message

            if msg.content:
                assistant_blocks.append({"type": "text", "text": msg.content})

            tool_calls = msg.tool_calls or []
            for tc in tool_calls:
                args = tc.function.arguments or "{}"
                payload = json.loads(args)
                assistant_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": payload,
                    }
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
            tool_result_msgs: list[dict[str, Any]] = []
            for b in assistant_blocks:
                if b["type"] != "tool_use":
                    continue
                out, is_error = tool_runner(b["name"], b["input"])
                used_tools.append(b["name"])
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": b["id"],
                        "is_error": is_error,
                        "content": [{"type": "text", "text": str(out)}],
                    }
                )
                tool_result_msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": b["id"],
                        "content": str(out),
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            oa_messages.extend(tool_result_msgs)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "messages": messages,
            "model_calls": calls,
            "tools_used": used_tools,
            "usage": turn_usage,
            "cost_usd": estimate_cost_usd(turn_usage),
            "latency_ms": elapsed_ms,
        }
