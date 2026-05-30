#!/usr/bin/env python3
"""Run Terminal-Bench 2.0 on Harbor with Laguna XS.2 via Poolside auth.

The Pool CLI stores an authenticated Poolside API URL and token locally. Harbor
does not speak to `pool exec` directly, so this wrapper uses the same credential
to call Poolside's OpenAI-compatible API through Harbor's Terminus 2 agent.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


DEFAULT_MODEL_ID = "poolside/laguna-xs.2"
DEFAULT_DATASET = "terminal-bench@2.0"


def load_pool_credential(api_url: str | None) -> tuple[str, str]:
    credentials_path = Path.home() / ".config/poolside/credentials.json"
    if not credentials_path.exists():
        raise SystemExit(
            f"Poolside credentials not found at {credentials_path}. Run `pool login` first."
        )

    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    if not isinstance(credentials, list) or not credentials:
        raise SystemExit(f"No Poolside credentials found in {credentials_path}.")

    if api_url:
        requested = api_url.rstrip("/")
        for credential in credentials:
            if str(credential.get("apiUrl", "")).rstrip("/") == requested:
                return requested, str(credential["token"])
        raise SystemExit(f"No Poolside credential found for apiUrl={requested!r}.")

    credential = credentials[0]
    return str(credential["apiUrl"]).rstrip("/"), str(credential["token"])


def append_repeated_option(command: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        command.extend([flag, value])


def build_command(args: argparse.Namespace, api_base: str) -> list[str]:
    model_name = args.litellm_model or f"openai/{args.model_id}"
    command = [
        "uv",
        "run",
        "--extra",
        "harbor",
        "harbor",
        "run",
        "--dataset",
        args.dataset,
        "--agent",
        "terminus-2",
        "--model",
        model_name,
        "--env",
        args.env,
        "--n-concurrent",
        str(args.n_concurrent),
        "--jobs-dir",
        str(args.jobs_dir),
        "--agent-kwarg",
        f"api_base={api_base}",
        "--agent-kwarg",
        f"temperature={args.temperature}",
        "--max-retries",
        str(args.max_retries),
        "--yes",
    ]

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Terminal-Bench 2.0 with Harbor Terminus 2 and Poolside Laguna XS.2."
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--litellm-model",
        help="Override the LiteLLM model string. Defaults to openai/<model-id>.",
    )
    parser.add_argument("--pool-api-url", help="Poolside API URL. Defaults to the first pool credential.")
    parser.add_argument("--env", default="docker", choices=["docker", "daytona", "e2b", "modal", "runloop"])
    parser.add_argument("--jobs-dir", type=Path, default=Path("evals/tb2_laguna_pool"))
    parser.add_argument("--job-name")
    parser.add_argument("--n-concurrent", type=int, default=4)
    parser.add_argument("--n-tasks", type=int)
    parser.add_argument("--include-task-name", action="append", default=[])
    parser.add_argument("--exclude-task-name", action="append", default=[])
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--timeout-multiplier", type=float)
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--agent-env", action="append", default=[])
    parser.add_argument("--environment-kwarg", action="append", default=[])
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Keep task containers/images after trials. Useful for local Docker smoke debugging.",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Harbor command without executing it. Secrets are not printed.",
    )
    args = parser.parse_args()

    api_url, token = load_pool_credential(args.pool_api_url)
    api_base = f"{api_url}/v1"
    command = build_command(args, api_base)

    redacted_command = [
        part.replace(token, "<redacted>") if isinstance(part, str) else part
        for part in command
    ]
    print("Poolside API base:", api_base)
    print("Harbor command:", " ".join(redacted_command))

    if args.dry_run:
        return 0

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = token
    env["OPENAI_API_BASE"] = api_base
    env["OPENAI_BASE_URL"] = api_base

    completed = subprocess.run(command, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
