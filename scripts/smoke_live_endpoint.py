#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_json(base_url: str, api_key: str, method: str, path: str, body: object | None = None) -> dict[str, object]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method=method,
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return {
                "ok": True,
                "status": response.status,
                "elapsed_s": round(time.time() - started, 3),
                "json": json.loads(response.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "elapsed_s": round(time.time() - started, 3),
            "error": exc.read().decode(errors="replace")[:1000],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Redacted live Laguna endpoint smoke.")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--out", type=Path, default=Path("/tmp/laguna-live-endpoint-smoke.json"))
    args = parser.parse_args()

    env = {**load_env(args.env_file), **os.environ}
    base_url = env.get("LAGUNA_API_BASE", "")
    api_key = env.get("LAGUNA_API_KEY", "")
    if not base_url or not api_key:
        raise SystemExit("missing LAGUNA_API_BASE or LAGUNA_API_KEY")

    report: dict[str, object] = {
        "base_present": bool(base_url),
        "key_present": bool(api_key),
        "key_len": len(api_key),
    }
    models = request_json(base_url, api_key, "GET", "/models")
    report["models"] = models
    model_ids = []
    if models["ok"]:
        model_ids = [row.get("id") for row in models["json"].get("data", [])]  # type: ignore[union-attr]
    model = "laguna" if "laguna" in model_ids else (model_ids[0] if model_ids else "laguna")
    report["selected_model"] = model

    chat = request_json(
        base_url,
        api_key,
        "POST",
        "/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: warm"}],
            "max_tokens": 8,
            "temperature": 0,
        },
    )
    if chat["ok"]:
        message = chat["json"]["choices"][0]["message"]  # type: ignore[index,union-attr]
        report["chat"] = {
            "status": chat["status"],
            "elapsed_s": chat["elapsed_s"],
            "content": message.get("content"),
            "has_reasoning_content": "reasoning_content" in message,
        }
    else:
        report["chat"] = chat

    tool_chat = request_json(
        base_url,
        api_key,
        "POST",
        "/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": "Use the echo tool once with text set to warm."}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "description": "Echo text.",
                        "parameters": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    },
                }
            ],
            "tool_choice": "auto",
            "max_tokens": 64,
            "temperature": 0,
        },
    )
    if tool_chat["ok"]:
        message = tool_chat["json"]["choices"][0]["message"]  # type: ignore[index,union-attr]
        tool_calls = message.get("tool_calls") or []
        report["tool_chat"] = {
            "status": tool_chat["status"],
            "elapsed_s": tool_chat["elapsed_s"],
            "content": message.get("content"),
            "tool_call_count": len(tool_calls),
            "tool_call_names": [tool_call.get("function", {}).get("name") for tool_call in tool_calls],
            "has_reasoning_content": "reasoning_content" in message,
        }
    else:
        report["tool_chat"] = tool_chat

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
