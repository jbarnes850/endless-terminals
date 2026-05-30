"""Small Harbor Terminus 2 wrapper with a process-wide LLM request throttle."""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from harbor.llms.chat import Chat
from harbor.agents.terminus_2.terminus_2 import Terminus2
from harbor.llms.base import LLMResponse


class RateLimitedTerminus2(Terminus2):
    _llm_lock = asyncio.Lock()
    _last_llm_call_started_at = 0.0

    def __init__(
        self,
        *args: Any,
        min_request_interval: float = 3.2,
        rate_limit_max_wait: float = 90.0,
        **kwargs: Any,
    ):
        self._min_request_interval = min_request_interval
        self._rate_limit_max_wait = rate_limit_max_wait
        super().__init__(*args, **kwargs)

    @staticmethod
    def name() -> str:
        return "rate-limited-terminus-2"

    async def _query_llm(self, *args: Any, **kwargs: Any) -> LLMResponse:
        chat = kwargs.get("chat") if "chat" in kwargs else args[0]
        prompt = kwargs.get("prompt") if "prompt" in kwargs else args[1]

        async with self._llm_lock:
            while True:
                await self._wait_for_interval()
                try:
                    start_time = time.time()
                    llm_response = await self._chat_without_retries(
                        chat,
                        prompt,
                        **self._llm_call_kwargs,
                    )
                    request_time_ms = (time.time() - start_time) * 1000
                    self._api_request_times.append(request_time_ms)
                    return llm_response
                except Exception as exc:
                    wait_s = self._rate_limit_wait_seconds(exc)
                    if wait_s is None:
                        raise
                    self.logger.warning(
                        "Provider rate limit hit; sleeping %.1fs before retrying.",
                        wait_s,
                    )
                    await asyncio.sleep(wait_s)

    async def _wait_for_interval(self) -> None:
        now = time.monotonic()
        wait_s = self._min_request_interval - (
            now - self.__class__._last_llm_call_started_at
        )
        if wait_s > 0:
            await asyncio.sleep(wait_s)
        self.__class__._last_llm_call_started_at = time.monotonic()

    def _rate_limit_wait_seconds(self, exc: Exception) -> float | None:
        text = str(exc)
        if "Rate limit exceeded" not in text and "code\":429" not in text:
            return None

        reset_match = re.search(r'"X-RateLimit-Reset":"?(\d+)"?', text)
        if reset_match:
            reset_ms = int(reset_match.group(1))
            wait_s = max(1.0, reset_ms / 1000 - time.time() + 2.0)
            return min(wait_s, self._rate_limit_max_wait)

        try:
            payload_start = text.index("{")
            payload = json.loads(text[payload_start:])
            headers = payload.get("error", {}).get("metadata", {}).get("headers", {})
            reset_ms = int(headers["X-RateLimit-Reset"])
            wait_s = max(1.0, reset_ms / 1000 - time.time() + 2.0)
            return min(wait_s, self._rate_limit_max_wait)
        except Exception:
            return min(60.0, self._rate_limit_max_wait)

    async def _chat_without_retries(
        self,
        chat: Chat,
        prompt: str,
        logging_path: Any = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Mirror Harbor Chat.chat while bypassing LiteLLM.call tenacity retries."""

        model = chat._model
        call = model.call
        undecorated_call = getattr(call, "__wrapped__", None)
        if undecorated_call is None:
            llm_response = await call(
                prompt=prompt,
                message_history=chat._messages,
                logging_path=logging_path,
                previous_response_id=chat._last_response_id,
                **kwargs,
            )
        else:
            llm_response = await undecorated_call(
                model,
                prompt=prompt,
                message_history=chat._messages,
                logging_path=logging_path,
                previous_response_id=chat._last_response_id,
                **kwargs,
            )

        if llm_response.response_id is not None:
            chat._last_response_id = llm_response.response_id

        usage = llm_response.usage
        if usage is not None:
            chat._cumulative_input_tokens += usage.prompt_tokens
            chat._cumulative_output_tokens += usage.completion_tokens
            chat._cumulative_cache_tokens += usage.cache_tokens
            chat._cumulative_cost += usage.cost_usd

        chat._accumulate_rollout_details(llm_response)

        assistant_message = {"role": "assistant", "content": llm_response.content}
        if chat._interleaved_thinking and llm_response.reasoning_content:
            assistant_message["reasoning_content"] = llm_response.reasoning_content

        chat._messages.extend(
            [
                {"role": "user", "content": prompt},
                assistant_message,
            ]
        )
        return llm_response
