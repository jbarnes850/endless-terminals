"""Harbor Terminus 2 variant that calls Poolside Laguna with native tools."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import litellm

from harbor.agents.terminus_2.terminus_2 import Command, Terminus2
from harbor.llms.base import BaseLLM, LLMResponse
from harbor.models.metric import UsageInfo


KEYSTROKES_TOOL = {
    "type": "function",
    "function": {
        "name": "keystrokes",
        "description": "Send exact keystrokes to the persistent terminal.",
        "parameters": {
            "type": "object",
            "properties": {
                "keystrokes": {
                    "type": "string",
                    "description": "Exact keystrokes to send. End shell commands with a newline.",
                },
                "duration": {
                    "type": "number",
                    "description": "Seconds to wait after sending these keystrokes.",
                },
            },
            "required": ["keystrokes"],
        },
    },
}

BASH_COMMAND_TOOL = {
    "type": "function",
    "function": {
        "name": "bash_command",
        "description": "Run a shell command in the persistent terminal.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run. End commands with a newline when appropriate.",
                },
                "duration": {
                    "type": "number",
                    "description": "Seconds to wait after sending the command.",
                },
            },
            "required": ["command"],
        },
    },
}

DONE_TOOL = {
    "type": "function",
    "function": {
        "name": "done",
        "description": "Call only when the task is complete and verified.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Short statement of the verification performed.",
                }
            },
            "required": ["reason"],
        },
    },
}


def _load_pool_credential(api_url: str | None = None) -> tuple[str, str]:
    credentials_path = Path.home() / ".config/poolside/credentials.json"
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    if not isinstance(credentials, list) or not credentials:
        raise RuntimeError(f"No Poolside credentials found in {credentials_path}")
    if api_url:
        requested = api_url.rstrip("/")
        for credential in credentials:
            if str(credential.get("apiUrl", "")).rstrip("/") == requested:
                return requested, str(credential["token"])
        raise RuntimeError(f"No Poolside credential found for apiUrl={requested!r}")
    credential = credentials[0]
    return str(credential["apiUrl"]).rstrip("/"), str(credential["token"])


def _parse_tool_arguments(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _plain_text(value: str) -> str:
    value = re.sub(r"<[^>\n]{1,80}>", " ", value)
    return value.replace("<", "[").replace(">", "]").strip()


def _extract_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for call in message.get("tool_calls") or []:
        function = _field(call, "function", {}) or {}
        name = _field(function, "name")
        args = _parse_tool_arguments(_field(function, "arguments"))
        if name:
            extracted.append(
                {
                    "id": _field(call, "id"),
                    "name": name,
                    "arguments": args,
                }
            )
    return extracted


def _tool_calls_to_summary(message: dict[str, Any]) -> str:
    content = str(message.get("content") or "").replace("</assistant>", "").strip()
    reasoning = str(message.get("reasoning_content") or "").strip()
    analysis = _plain_text(reasoning or content or "Selected the next terminal action.")

    plan_parts: list[str] = []
    for call in _extract_tool_calls(message):
        name = call["name"]
        args = call["arguments"]
        if name in {"keystrokes", "bash_command"}:
            keystrokes = str(
                args.get("keystrokes") or args.get("command") or args.get("cmd") or ""
            )
            duration = float(args.get("duration") or 1.0)
            command_preview = _plain_text(keystrokes).replace("\n", "\\n")[:160]
            plan_parts.append(
                f"Call {name} for {duration:.1f}s: {command_preview}"
            )
        elif name == "done":
            reason = _plain_text(str(args.get("reason") or "Task complete."))
            plan_parts.append(f"Call done: {reason}")

    plan = _plain_text(" ".join(plan_parts) or "No supported tool call emitted.")
    return f"Analysis: {analysis}\nPlan: {plan}"


def _has_supported_tool_call(message: dict[str, Any]) -> bool:
    for call in message.get("tool_calls") or []:
        function = _field(call, "function", {}) or {}
        if _field(function, "name") in {"keystrokes", "bash_command", "done"}:
            return True
    return False


class PoolLagunaToolLLM(BaseLLM):
    def __init__(
        self,
        model_name: str,
        *,
        api_base: str | None = None,
        temperature: float | None = None,
        max_completion_tokens: int = 2048,
        rate_limit_max_retries: int = 8,
        rate_limit_base_sleep: float = 5.0,
        request_timeout: float = 120.0,
        **_: Any,
    ):
        super().__init__()
        credential_api_url, self._api_key = _load_pool_credential(
            api_base[:-3] if api_base and api_base.endswith("/v1") else api_base
        )
        self._api_base = api_base or f"{credential_api_url}/v1"
        self._model_name = model_name.removeprefix("openai/")
        self._temperature = temperature
        self._max_completion_tokens = max_completion_tokens
        self._rate_limit_max_retries = rate_limit_max_retries
        self._rate_limit_base_sleep = rate_limit_base_sleep
        self._request_timeout = request_timeout

    async def call(
        self,
        prompt: str,
        message_history: list[dict[str, Any]] | None = None,
        **_: Any,
    ) -> LLMResponse:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are controlling a persistent Linux terminal through native "
                    "tool calls. Ignore any XML or JSON response-format instructions "
                    "in the task scaffold. On every turn call exactly one tool: "
                    "bash_command for shell work, keystrokes only for interactive "
                    "terminal control, or done after you have verified completion. "
                    "Do not describe a command without calling a tool."
                ),
            },
            *list(message_history or []),
            {"role": "user", "content": prompt},
        ]
        kwargs: dict[str, Any] = {
            "model": f"openai/{self._model_name}",
            "api_base": self._api_base,
            "api_key": self._api_key,
            "messages": messages,
            "tools": [BASH_COMMAND_TOOL, KEYSTROKES_TOOL, DONE_TOOL],
            "tool_choice": "required",
            "max_completion_tokens": self._max_completion_tokens,
            "timeout": self._request_timeout,
        }
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature

        response = await self._completion_with_backoff(kwargs)
        choice = response["choices"][0]
        message = dict(choice["message"])
        finish_reason = choice.get("finish_reason")

        if finish_reason != "length" and not _has_supported_tool_call(message):
            forced_kwargs = dict(kwargs)
            forced_kwargs["messages"] = messages + [
                {
                    "role": "user",
                    "content": (
                        "Your previous response did not call a terminal tool. "
                        "Call the bash_command tool now with the next shell action."
                    ),
                }
            ]
            forced_kwargs["tool_choice"] = {
                "type": "function",
                "function": {"name": "bash_command"},
            }
            try:
                response = await self._completion_with_backoff(forced_kwargs)
                choice = response["choices"][0]
                message = dict(choice["message"])
                finish_reason = choice.get("finish_reason")
            except Exception:
                pass

        content = _tool_calls_to_summary(message)
        usage = response.get("usage") or {}
        details = _field(usage, "prompt_tokens_details", {}) or {}
        return LLMResponse(
            content=content,
            reasoning_content=message.get("reasoning_content"),
            model_name=response.get("model") or self._model_name,
            usage=UsageInfo(
                prompt_tokens=int(_field(usage, "prompt_tokens", 0) or 0),
                completion_tokens=int(_field(usage, "completion_tokens", 0) or 0),
                cache_tokens=int(_field(details, "cached_tokens", 0) or 0),
                cost_usd=0.0,
            ),
            extra={
                "raw_content": message.get("content"),
                "tool_calls": _extract_tool_calls(message),
                "finish_reason": finish_reason,
                "truncated": finish_reason == "length",
            },
        )

    async def _completion_with_backoff(self, kwargs: dict[str, Any]) -> Any:
        for attempt in range(self._rate_limit_max_retries + 1):
            try:
                return await litellm.acompletion(**kwargs)
            except (
                litellm.APIConnectionError,
                litellm.RateLimitError,
                litellm.ServiceUnavailableError,
                litellm.Timeout,
            ):
                if attempt >= self._rate_limit_max_retries:
                    raise
                sleep_s = self._rate_limit_base_sleep * (2**attempt)
                await asyncio.sleep(min(sleep_s, 60.0))
        raise RuntimeError("unreachable")

    def get_model_context_limit(self) -> int:
        return 262144

    def get_model_output_limit(self) -> int | None:
        return 32768


class PoolLagunaTerminus2(Terminus2):
    def __init__(
        self,
        *args: Any,
        parser_name: str = "xml",
        max_completion_tokens: int = 2048,
        rate_limit_max_retries: int = 8,
        rate_limit_base_sleep: float = 5.0,
        request_timeout: float = 120.0,
        **kwargs: Any,
    ):
        self._pool_max_completion_tokens = max_completion_tokens
        self._pool_rate_limit_max_retries = rate_limit_max_retries
        self._pool_rate_limit_base_sleep = rate_limit_base_sleep
        self._pool_request_timeout = request_timeout
        super().__init__(*args, parser_name=parser_name, **kwargs)

    @staticmethod
    def name() -> str:
        return "pool-laguna-terminus-2"

    def _init_llm(self, *args: Any, **kwargs: Any) -> BaseLLM:
        return PoolLagunaToolLLM(
            model_name=kwargs["model_name"],
            temperature=kwargs.get("temperature"),
            api_base=kwargs.get("api_base"),
            max_completion_tokens=self._pool_max_completion_tokens,
            rate_limit_max_retries=self._pool_rate_limit_max_retries,
            rate_limit_base_sleep=self._pool_rate_limit_base_sleep,
            request_timeout=self._pool_request_timeout,
        )

    async def _handle_llm_interaction(
        self,
        chat: Any,
        prompt: str,
        original_instruction: str = "",
        session: Any | None = None,
    ) -> tuple[list[Command], bool, str, str, str, LLMResponse]:
        llm_response = await self._query_llm(
            chat, prompt, original_instruction, session
        )

        commands: list[Command] = []
        task_complete = False
        plan_parts: list[str] = []
        tool_calls = (llm_response.extra or {}).get("tool_calls") or []

        for call in tool_calls:
            name = call.get("name")
            args = call.get("arguments") or {}
            if name in {"keystrokes", "bash_command"}:
                keystrokes = str(
                    args.get("keystrokes")
                    or args.get("command")
                    or args.get("cmd")
                    or ""
                )
                if keystrokes and not keystrokes.endswith("\n") and not keystrokes.startswith("C-"):
                    keystrokes += "\n"
                duration = float(args.get("duration") or 1.0)
                commands.append(
                    Command(keystrokes=keystrokes, duration_sec=min(duration, 60.0))
                )
                plan_parts.append(f"Run {name}.")
            elif name == "done":
                task_complete = True
                plan_parts.append("Mark task complete.")

        raw_content = str((llm_response.extra or {}).get("raw_content") or "")
        analysis = _plain_text(
            llm_response.reasoning_content
            or raw_content
            or "Selected the next terminal action."
        )

        if not commands and not task_complete:
            feedback = "WARNINGS: Poolside response did not include a supported tool call."
            plan = "No terminal action was emitted."
        else:
            feedback = ""
            plan = " ".join(plan_parts)

        return commands, task_complete, feedback, analysis, plan, llm_response
