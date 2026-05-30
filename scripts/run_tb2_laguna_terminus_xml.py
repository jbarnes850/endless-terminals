#!/usr/bin/env python3
"""Run Terminal-Bench 2.0 with Harbor Terminus 2 XML and Laguna XS.2.

This runner is intentionally separate from `run_tb2_laguna_pool.py`. It does not
use Poolside native tool calls or Pool CLI auth. Instead it treats Laguna as a
plain text completion model and lets Harbor's Terminus 2 XML parser extract
terminal actions from the model response.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_DATASET = "terminal-bench@2.0"
DEFAULT_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL_ID = "poolside/laguna-xs.2:free"
DEFAULT_AGENT_IMPORT_PATH = "endless_harbor.rate_limited_terminus:RateLimitedTerminus2"


def append_repeated_option(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        command.extend([flag, value])


def build_command(args: argparse.Namespace) -> list[str]:
    litellm_model = args.litellm_model or f"openrouter/{args.model_id}"
    llm_call_kwargs = {
        "max_tokens": args.max_completion_tokens,
        "timeout": args.request_timeout,
    }
    model_info = {
        "max_input_tokens": args.context_length,
        "max_output_tokens": args.model_max_output_tokens,
        "input_cost_per_token": 0,
        "output_cost_per_token": 0,
    }
    command = [
        "uv",
        "run",
        "--extra",
        "harbor",
        "harbor",
        "run",
        "--dataset",
        args.dataset,
        "--agent-import-path",
        args.agent_import_path,
        "--model",
        litellm_model,
        "--env",
        args.env,
        "--n-concurrent",
        str(args.n_concurrent),
        "--jobs-dir",
        str(args.jobs_dir),
        "--agent-kwarg",
        "parser_name=xml",
        "--agent-kwarg",
        f"temperature={args.temperature}",
        "--agent-kwarg",
        f"llm_call_kwargs={json.dumps(llm_call_kwargs, separators=(',', ':'))}",
        "--agent-kwarg",
        f"model_info={json.dumps(model_info, separators=(',', ':'))}",
        "--agent-kwarg",
        f"min_request_interval={args.min_request_interval}",
        "--max-retries",
        str(args.max_retries),
        "--yes",
    ]
    if args.api_base:
        command.extend(["--agent-kwarg", f"api_base={args.api_base.rstrip('/')}"])
    if args.job_name:
        command.extend(["--job-name", args.job_name])
    if args.n_tasks is not None:
        command.extend(["--n-tasks", str(args.n_tasks)])
    if args.max_turns is not None:
        command.extend(["--agent-kwarg", f"max_turns={args.max_turns}"])
        command.extend(["--agent-kwarg", "suppress_max_turns_warning=True"])
    if args.timeout_multiplier is not None:
        command.extend(["--timeout-multiplier", str(args.timeout_multiplier)])
    if args.quiet:
        command.append("--quiet")
    if args.force_build:
        command.append("--force-build")
    if args.no_delete:
        command.append("--no-delete")

    append_repeated_option(command, "--include-task-name", args.include_task_name)
    append_repeated_option(command, "--exclude-task-name", args.exclude_task_name)
    append_repeated_option(command, "--agent-env", args.agent_env)
    append_repeated_option(command, "--environment-kwarg", args.environment_kwarg)
    return command


def probe_chat(args: argparse.Namespace, api_key: str) -> None:
    request = Request(
        f"{args.api_base.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": args.model_id,
                "messages": [{"role": "user", "content": "Return exactly OK."}],
                "max_tokens": 64,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Terminus XML provider probe failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"Terminus XML provider probe failed: {exc}") from exc

    if not payload.get("choices"):
        raise SystemExit(f"Provider probe returned no choices: {payload!r}")
    content = payload["choices"][0]["message"].get("content") or ""
    finish_reason = payload["choices"][0].get("finish_reason")
    usage = payload.get("usage") or {}
    print(
        "Terminus XML provider probe passed:",
        f"finish_reason={finish_reason}",
        f"content_chars={len(content.strip())}",
        f"prompt_tokens={usage.get('prompt_tokens')}",
        f"completion_tokens={usage.get('completion_tokens')}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Terminal-Bench 2.0 with Harbor Terminus 2 XML and Laguna XS.2."
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--agent-import-path", default=DEFAULT_AGENT_IMPORT_PATH)
    parser.add_argument(
        "--litellm-model",
        help="LiteLLM model string. Defaults to openrouter/<model-id>.",
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--env", default="docker", choices=["docker", "daytona", "e2b", "modal", "runloop"])
    parser.add_argument("--jobs-dir", type=Path, default=Path("evals/tb2_laguna_terminus_xml"))
    parser.add_argument("--job-name")
    parser.add_argument("--n-concurrent", type=int, default=1)
    parser.add_argument("--n-tasks", type=int)
    parser.add_argument("--include-task-name", action="append", default=[])
    parser.add_argument("--exclude-task-name", action="append", default=[])
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-completion-tokens", type=int, default=2048)
    parser.add_argument("--context-length", type=int, default=131072)
    parser.add_argument("--model-max-output-tokens", type=int, default=8192)
    parser.add_argument("--min-request-interval", type=float, default=3.2)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--timeout-multiplier", type=float)
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--agent-env", action="append", default=[])
    parser.add_argument("--environment-kwarg", action="append", default=[])
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--no-delete", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--skip-probe", action="store_true")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    command = build_command(args)
    print("Provider API base:", args.api_base)
    print("Harbor command:", " ".join(command))

    if args.dry_run:
        return 0

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Missing API key env var: {args.api_key_env}")

    if not args.skip_probe:
        probe_chat(args, api_key)
    if args.probe_only:
        return 0

    env = os.environ.copy()
    # LiteLLM's OpenRouter provider reads OPENROUTER_API_KEY. Also set OpenAI
    # names for explicit OpenAI-compatible routes.
    env["OPENROUTER_API_KEY"] = api_key
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_API_BASE"] = args.api_base.rstrip("/")
    env["OPENAI_BASE_URL"] = args.api_base.rstrip("/")

    completed = subprocess.run(command, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
