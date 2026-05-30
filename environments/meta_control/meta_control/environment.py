from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
import json
from pathlib import Path
import re
import statistics
from typing import Any

import verifiers as vf
from tasksets import HarborTaskset, HarborTasksetConfig
from verifiers.utils.interception_utils import serialize_tool_defs
from verifiers.v1.utils.program_utils import (
    merge_task_program,
    merge_task_sandbox,
    program_option_mapping,
)
from verifiers.v1.utils.sandbox_program_utils import python_runtime_command
from verifiers.v1.utils.sandbox_utils import (
    VF_STATE_INPUT_PATH_KEY,
    read_sandbox_artifact,
    run_sandbox_command,
)
from verifiers.v1.utils.serialization_utils import serializable


LAGUNA_XML_STATE_INPUT_PATH = "/tmp/meta_control_laguna_state_in.json"
LAGUNA_XML_STATE_OUTPUT_PATH = "/tmp/meta_control_laguna_state_out.json"
LAGUNA_XML_RUNNER_PATH = "/tmp/meta_control_laguna_xml_runner.py"
LAGUNA_XML_TOOL_DEFS_PATH = "/tmp/meta_control_laguna_tool_defs.json"
META_CONTROL_TASK_SETUP_PATH = "/tmp/meta_control_task_setup.sh"


class MetaControlTasksetConfig(HarborTasksetConfig):
    bundle_package: str | None = __name__


class MetaControlHarnessConfig(vf.HarnessConfig):
    # Native Verifiers base program: Prime-RL samples Laguna through the
    # laguna-xs.2 renderer, then Verifiers executes model tool calls inside the
    # task sandbox and Harbor scores the hidden final verifier.
    system_prompt: vf.PromptInput | vf.SystemPromptConfig | None = [
        {
            "role": "system",
            "content": (
                "You are operating a terminal task. Keep a concise sense of the target deliverable, "
                "verify the actual files or command outputs after each meaningful step, change approach "
                "when an action makes no progress, and stop only after the required final state has been checked."
            ),
        }
    ]
    program: vf.ProgramConfig = vf.ProgramConfig(sandbox=True)
    sandbox: vf.SandboxConfig = vf.SandboxConfig(
        workdir="/app",
        command_timeout=900,
        timeout_minutes=120,
    )
    max_turns: int = 16
    gated_progress_weight: float = 0.30
    stop_success_reward: float = 0.15
    stop_run_past_complete_penalty: float = 0.10
    stop_early_penalty: float = 0.15
    stop_very_early_penalty: float = 0.20
    repeat_action_unit_penalty: float = 0.02
    repeat_action_cap: float = 0.05
    dominant_action_penalty: float = 0.03
    success_repeat_penalty_cap: float = 0.02
    malformed_tool_unit_penalty: float = 0.05
    malformed_tool_cap: float = 0.10
    context_budget_penalty: float = 0.20
    turn_cost_unit: float = 0.005
    turn_cost_cap: float = 0.02
    success_turn_cost_cap: float = 0.01


class MetaControlHarness(vf.Harness[MetaControlHarnessConfig]):
    config: MetaControlHarnessConfig

    def sandbox_base_program(self, program: dict[str, Any], sandbox_config: vf.SandboxConfig):
        async def run(task: vf.Task, state: vf.State) -> vf.State:
            merged_program = merge_task_program(program, task, kind="base")
            merged_program = with_task_environment_setup(merged_program, task)
            prepared_program = self.prepare_sandbox_program(merged_program, state)
            prepared_sandbox = self.prepare_sandbox_config(
                merge_task_sandbox(sandbox_config, task),
                merged_program,
            )
            runner_program = laguna_xml_runner_program(
                prepared_program,
                self.runtime.tool_defs(state) or [],
                max_turns=state.get_max_turns(self.config.max_turns),
            )
            command_record = state.get("command")
            await run_sandbox_command(
                runner_program,
                prepared_sandbox,
                task,
                state,
                self.runtime,
            )
            lease = self.runtime.active_program_sandbox_lease(state)
            if lease is None:
                raise RuntimeError("Laguna XML sandbox program has no active sandbox lease.")
            output = json.loads(
                await read_sandbox_artifact(
                    lease.client,
                    lease.id,
                    LAGUNA_XML_STATE_OUTPUT_PATH,
                )
            )
            if not isinstance(output, dict):
                raise RuntimeError("Laguna XML sandbox program did not return a state patch.")
            patch = dict(output)
            stop_condition = patch.pop("stop_condition", None)
            is_truncated = patch.pop("is_truncated", None)
            error = patch.pop("error", None)
            is_completed = patch.pop("is_completed", None)
            if stop_condition is not None:
                state._set_stop_condition(str(stop_condition), overwrite=True)
            if is_truncated is not None:
                state._set_truncated(bool(is_truncated), overwrite=True)
            if error is not None:
                state._set_error(error)
            if is_completed is not None:
                state._set_completed(bool(is_completed))
            patch_artifacts = patch.pop("artifacts", None)
            if isinstance(patch_artifacts, dict):
                state.setdefault("artifacts", {})
                state["artifacts"].update(dict(patch_artifacts))
            state.update(patch)
            ensure_top_level_sampling_args(state)
            if command_record is not None:
                state["command"] = command_record
            return state

        return run

    @vf.metric
    async def tool_call_count(self, state: vf.State) -> float:
        return float(len(action_fingerprints(state)))

    @vf.metric
    async def unique_action_count(self, state: vf.State) -> float:
        return float(len(set(action_fingerprints(state))))

    @vf.metric
    async def adjacent_repeat_count(self, state: vf.State) -> float:
        actions = action_fingerprints(state)
        return float(sum(left == right for left, right in zip(actions, actions[1:])))

    @vf.metric
    async def dominant_action_share(self, state: vf.State) -> float:
        actions = action_fingerprints(state)
        if not actions:
            return 0.0
        counts = {action: actions.count(action) for action in set(actions)}
        return float(max(counts.values()) / len(actions))

    @vf.metric
    async def unchanged_state_rate(self, state: vf.State) -> float:
        observations = action_observation_fingerprints(state)
        if len(observations) < 2:
            return 0.0
        repeats = sum(left == right for left, right in zip(observations, observations[1:]))
        return float(repeats / (len(observations) - 1))

    @vf.metric
    async def natural_stop(self, state: vf.State) -> float:
        return float(state.get("stop_condition") == "no_tools")

    @vf.metric
    async def max_turn_stop(self, state: vf.State) -> float:
        return float(state.get("stop_condition") == "max_turns_reached")

    @vf.metric
    async def checkpoint_count(self, state: vf.State) -> float:
        return float(len(checkpoint_outcomes(state)))

    @vf.metric
    async def checkpoint_prefix_share(self, state: vf.State) -> float:
        return checkpoint_prefix_share(state)

    @vf.metric
    async def tool_error_count(self, state: vf.State) -> float:
        return float(len(tool_error_messages(state)))

    @vf.metric
    async def raw_observation_tokens(self, state: vf.State) -> float:
        return float(meta_control_rollout_metrics(state).get("raw_observation_tokens", 0.0) or 0.0)

    @vf.metric
    async def compacted_observation_tokens(self, state: vf.State) -> float:
        return float(meta_control_rollout_metrics(state).get("compacted_observation_tokens", 0.0) or 0.0)

    @vf.metric
    async def truncated_bytes(self, state: vf.State) -> float:
        return float(meta_control_rollout_metrics(state).get("truncated_bytes", 0.0) or 0.0)

    @vf.metric
    async def overlong_prompt_count(self, state: vf.State) -> float:
        return float(meta_control_rollout_metrics(state).get("overlong_prompt_count", 0.0) or 0.0)

    @vf.metric
    async def max_prompt_estimated_tokens(self, state: vf.State) -> float:
        return float(meta_control_rollout_metrics(state).get("max_prompt_estimated_tokens", 0.0) or 0.0)

    @vf.reward(priority=-5)
    async def gated_progress(self, state: vf.State) -> float:
        if harbor_success(state):
            return self.config.gated_progress_weight
        if state.get("harbor_error"):
            return 0.0
        return self.config.gated_progress_weight * checkpoint_prefix_share(state)

    @vf.reward(priority=-10)
    async def stop_quality(self, state: vf.State) -> float:
        success = harbor_success(state)
        stop_condition = state.get("stop_condition")
        turns = len(state.get("trajectory") or [])
        if success and stop_condition == "no_tools":
            return self.config.stop_success_reward
        if success and stop_condition == "max_turns_reached":
            return -self.config.stop_run_past_complete_penalty
        if not success and stop_condition == "no_tools":
            return -self.config.stop_very_early_penalty if turns <= 2 else -self.config.stop_early_penalty
        return 0.0

    @vf.reward(priority=-20)
    async def nonprogress_penalty(self, state: vf.State) -> float:
        actions = action_fingerprints(state)
        if len(actions) < 2:
            return 0.0
        adjacent_repeats = sum(left == right for left, right in zip(actions, actions[1:]))
        dominant_share = max(actions.count(action) for action in set(actions)) / len(actions)
        penalty = min(self.config.repeat_action_cap, self.config.repeat_action_unit_penalty * adjacent_repeats)
        if len(actions) >= 8 and dominant_share >= 0.50:
            penalty += self.config.dominant_action_penalty
        if harbor_success(state):
            penalty = min(penalty, self.config.success_repeat_penalty_cap)
        return -float(penalty)

    @vf.metric
    async def repeat_action_penalty(self, state: vf.State) -> float:
        return await self.nonprogress_penalty(state)

    @vf.reward(priority=-30)
    async def malformed_tool_penalty(self, state: vf.State) -> float:
        return -min(self.config.malformed_tool_cap, self.config.malformed_tool_unit_penalty * len(tool_error_messages(state)))

    @vf.reward(priority=-35)
    async def context_budget_penalty(self, state: vf.State) -> float:
        if state.get("stop_condition") == "context_budget_exceeded":
            return -self.config.context_budget_penalty
        return 0.0

    @vf.reward(priority=-40)
    async def turn_cost(self, state: vf.State) -> float:
        turns = len(state.get("trajectory") or [])
        if harbor_success(state):
            return -min(self.config.success_turn_cost_cap, self.config.turn_cost_unit * turns)
        return -min(self.config.turn_cost_cap, self.config.turn_cost_unit * turns)

    @vf.metric(stage="group")
    async def reward_group_std(self, states: list[vf.State]) -> list[float]:
        rewards = [float(state.get("reward", 0.0) or 0.0) for state in states]
        std = statistics.pstdev(rewards) if len(rewards) > 1 else 0.0
        return [float(std)] * len(states)

    @vf.metric(stage="group")
    async def low_reward_variance_group(self, states: list[vf.State]) -> list[float]:
        rewards = [float(state.get("reward", 0.0) or 0.0) for state in states]
        std = statistics.pstdev(rewards) if len(rewards) > 1 else 0.0
        value = float(std < 1e-5)
        return [value] * len(states)


def laguna_xml_runner_program(
    program: Mapping[str, Any],
    runtime_tool_defs: list[vf.Tool],
    *,
    max_turns: int,
) -> dict[str, Any]:
    files = program_option_mapping(program.get("files"), "program.files")
    remote_tool_defs = serialize_tool_defs(runtime_tool_defs, "openai_chat_completions")
    remote_tool_names = {
        str(tool.get("function", {}).get("name") or tool.get("name"))
        for tool in remote_tool_defs
        if isinstance(tool, Mapping)
    }
    terminal_tool_defs = [
        tool
        for tool in laguna_terminal_tool_defs()
        if tool["function"]["name"] not in remote_tool_names
    ]
    files[LAGUNA_XML_TOOL_DEFS_PATH] = json.dumps(
        {
            "tools": serializable([*terminal_tool_defs, *remote_tool_defs]),
            "remote_tool_names": sorted(name for name in remote_tool_names if name),
            "max_turns": max_turns,
        }
    )
    files[LAGUNA_XML_RUNNER_PATH] = LAGUNA_XML_RUNNER_SOURCE
    merged = dict(program)
    merged["files"] = files
    merged["command"] = python_runtime_command(LAGUNA_XML_RUNNER_PATH)
    merged[VF_STATE_INPUT_PATH_KEY] = LAGUNA_XML_STATE_INPUT_PATH
    return merged


def with_task_environment_setup(program: Mapping[str, Any], task: Mapping[str, Any]) -> dict[str, Any]:
    setup_script = task_environment_setup_script(task)
    if setup_script is None:
        return dict(program)
    files = program_option_mapping(program.get("files"), "program.files")
    files[META_CONTROL_TASK_SETUP_PATH] = setup_script
    env = program_option_mapping(program.get("env"), "program.env")
    if env.get("AGENT_WORKDIR") in (None, "", "/app"):
        env["AGENT_WORKDIR"] = "/home/user"
    setup = []
    raw_setup = program.get("setup")
    if isinstance(raw_setup, list):
        setup.extend(raw_setup)
    elif raw_setup:
        setup.append(raw_setup)
    setup.append(f"bash {META_CONTROL_TASK_SETUP_PATH}")
    merged = dict(program)
    merged["files"] = files
    merged["env"] = env
    merged["setup"] = setup
    merged["setup_timeout"] = int(task_setup_timeout(task))
    return merged


def task_setup_timeout(task: Mapping[str, Any]) -> float:
    harbor = task.get("harbor")
    config = harbor.get("config") if isinstance(harbor, Mapping) else None
    environment = config.get("environment") if isinstance(config, Mapping) else None
    if isinstance(environment, Mapping):
        value = environment.get("build_timeout_sec")
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
    return 900.0


def task_environment_setup_script(task: Mapping[str, Any]) -> str | None:
    task_dir_value = task.get("task_dir")
    if not isinstance(task_dir_value, str) or not task_dir_value:
        return None
    dockerfile = Path(task_dir_value) / "environment" / "Dockerfile"
    if not dockerfile.exists():
        return None
    setup_body = extract_endless_docker_post(dockerfile.read_text(encoding="utf-8"))
    if setup_body is None:
        return None
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "export DEBIAN_FRONTEND=noninteractive",
            "if [ -f /tmp/meta_control_task_setup.done ]; then exit 0; fi",
            setup_body,
            "",
            "# Some generated tasks install local service starters instead of Docker CMDs.",
            "for starter in /usr/local/bin/start_*; do",
            "  if [ -x \"$starter\" ]; then",
            "    \"$starter\" || { echo \"meta-control setup starter failed: $starter\" >&2; exit 1; }",
            "  fi",
            "done",
            "touch /tmp/meta_control_task_setup.done",
            "",
        ]
    )


def extract_endless_docker_post(dockerfile_text: str) -> str | None:
    match = re.search(
        r"RUN <<'__ENDLESS_DOCKER_POST__'\n(?P<body>.*?)\n__ENDLESS_DOCKER_POST__",
        dockerfile_text,
        re.DOTALL,
    )
    if not match:
        return None
    return match.group("body").strip("\n")


def ensure_top_level_sampling_args(state: MutableMapping[str, Any]) -> None:
    sampling = state.get("sampling_args")
    if isinstance(sampling, Mapping):
        state["sampling_args"] = dict(sampling)
        return
    runtime = state.get("runtime") or {}
    if not isinstance(runtime, Mapping):
        return
    runtime_sampling = runtime.get("sampling_args")
    if isinstance(runtime_sampling, Mapping):
        state["sampling_args"] = dict(runtime_sampling)


def laguna_terminal_tool_defs() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "shell",
                "description": "Run a shell command in the task sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cat",
                "description": "Print a file from the task sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read a file from the task sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "done",
                "description": "Stop after the required final state has been verified.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    ]


def parse_laguna_xml_tool_calls(content: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for index, match in enumerate(re.finditer(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)):
        block = match.group(1)
        arg_start = block.find("<arg_key>")
        if arg_start >= 0:
            name = block[:arg_start].strip()
            args_text = block[arg_start:]
        else:
            name = block.strip()
            args_text = ""
        arguments: dict[str, Any] = {}
        for arg_match in re.finditer(
            r"<arg_key>(.*?)</arg_key>\s*<arg_value>(.*?)</arg_value>",
            args_text,
            re.DOTALL,
        ):
            key = arg_match.group(1).strip()
            value_text = arg_match.group(2).strip()
            try:
                value: Any = json.loads(value_text)
            except json.JSONDecodeError:
                value = value_text
            arguments[key] = value
        if name:
            calls.append(
                {
                    "id": f"laguna_xml_call_{index}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(arguments, sort_keys=True),
                    },
                }
            )
    return calls


LAGUNA_XML_RUNNER_SOURCE = r"""
import asyncio
import json
import os
import re
import shlex
import subprocess
import time
import urllib.error
import urllib.request

from openai import AsyncOpenAI

STATE_INPUT_PATH = "/tmp/meta_control_laguna_state_in.json"
STATE_OUTPUT_PATH = "/tmp/meta_control_laguna_state_out.json"
TOOL_DEFS_PATH = "/tmp/meta_control_laguna_tool_defs.json"
DEFAULT_TOOL_OBSERVATION_CHAR_LIMIT = 6000
DEFAULT_PROMPT_TOKEN_BUDGET = 56000


def endpoint_token():
    return os.environ.get("OPENAI_API_KEY") or "intercepted"


def endpoint_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "meta-control-laguna-xml-runner",
        "Authorization": f"Bearer {endpoint_token()}",
    }


def vf_url(state, path):
    return f"{state['endpoint_root_url'].rstrip('/')}/vf/{path}"


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=endpoint_headers(), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=300.0) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode(errors="replace")) from exc
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


async def vf_post(state, path, payload):
    return await asyncio.to_thread(post_json, vf_url(state, path), payload)


async def call_remote_tool(state, name, arguments):
    payload = await vf_post(state, f"tools/{name}", {"arguments": arguments})
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload.get("result")


async def check_stop(state):
    payload = await vf_post(state, "stop", {})
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    if payload.get("done"):
        if payload.get("stop_condition"):
            state["stop_condition"] = payload["stop_condition"]
        return True
    return False


def sampling_args(state):
    raw = state.get("runtime", {}).get("sampling_args") or {}
    if not isinstance(raw, dict):
        raise RuntimeError("state.runtime.sampling_args must be a mapping.")
    return dict(raw)


def tool_observation_char_limit():
    raw = os.environ.get("META_CONTROL_TOOL_OBSERVATION_CHAR_LIMIT", str(DEFAULT_TOOL_OBSERVATION_CHAR_LIMIT))
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_TOOL_OBSERVATION_CHAR_LIMIT
    return max(512, value)


def approx_tokens(text):
    if not text:
        return 0
    return max(1, (len(str(text)) + 3) // 4)


def rollout_metrics(state):
    metrics = state.setdefault("meta_control_rollout_metrics", {})
    metrics.setdefault("raw_observation_tokens", 0)
    metrics.setdefault("compacted_observation_tokens", 0)
    metrics.setdefault("truncated_bytes", 0)
    metrics.setdefault("compaction_events", 0)
    metrics.setdefault("overlong_prompt_count", 0)
    metrics.setdefault("max_prompt_estimated_tokens", 0)
    return metrics


def record_observation_compaction(state, raw, compacted):
    metrics = rollout_metrics(state)
    metrics["raw_observation_tokens"] += approx_tokens(raw)
    metrics["compacted_observation_tokens"] += approx_tokens(compacted)
    truncated = max(0, len(str(raw).encode("utf-8")) - len(str(compacted).encode("utf-8")))
    metrics["truncated_bytes"] += truncated
    if truncated:
        metrics["compaction_events"] += 1


def compact_tool_observation(state, content):
    text = str(content)
    limit = tool_observation_char_limit()
    if len(text) <= limit:
        record_observation_compaction(state, text, text)
        return text
    marker = (
        f"\n[meta_control: tool output truncated from {len(text)} to {limit} characters; "
        "rerun a narrower command or inspect specific files if needed]\n"
    )
    if len(marker) >= limit:
        compacted = marker[:limit]
        record_observation_compaction(state, text, compacted)
        return compacted
    remaining = limit - len(marker)
    head = remaining // 2
    tail = remaining - head
    compacted = text[:head] + marker + text[-tail:]
    record_observation_compaction(state, text, compacted)
    return compacted


def prompt_token_budget():
    raw = os.environ.get("META_CONTROL_PROMPT_TOKEN_BUDGET", str(DEFAULT_PROMPT_TOKEN_BUDGET))
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_PROMPT_TOKEN_BUDGET
    return max(4096, value)


def estimated_prompt_tokens(messages):
    return approx_tokens(json.dumps(messages, separators=(",", ":"), ensure_ascii=False))


def record_prompt_size(state, messages):
    tokens = estimated_prompt_tokens(messages)
    metrics = rollout_metrics(state)
    metrics["max_prompt_estimated_tokens"] = max(int(metrics.get("max_prompt_estimated_tokens") or 0), tokens)
    return tokens


def model_name(state):
    model = state.get("runtime", {}).get("model")
    if not model:
        raise RuntimeError("Laguna XML runner requires state.runtime.model.")
    return model


def load_tool_config():
    data = json.loads(open(TOOL_DEFS_PATH, encoding="utf-8").read())
    return data.get("tools") or [], set(data.get("remote_tool_names") or []), int(data.get("max_turns") or 0)


def to_plain(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if hasattr(value, "model_dump_json"):
        return json.loads(value.model_dump_json(exclude_none=True))
    return json.loads(json.dumps(value))


def parse_json_args(raw):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def structured_tool_calls(message):
    calls = []
    for call in message.get("tool_calls") or []:
        if isinstance(call, dict):
            function = call.get("function") or {}
            name = function.get("name") or call.get("name")
            arguments = function.get("arguments", call.get("arguments", "{}"))
            call_id = call.get("id") or f"structured_call_{len(calls)}"
        else:
            function = getattr(call, "function", None)
            name = getattr(function, "name", None) or getattr(call, "name", None)
            arguments = getattr(function, "arguments", None) or getattr(call, "arguments", "{}")
            call_id = getattr(call, "id", None) or f"structured_call_{len(calls)}"
        if not name:
            continue
        calls.append(
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
                },
            }
        )
    return calls


def parse_laguna_xml_tool_calls(content):
    calls = []
    for index, match in enumerate(re.finditer(r"<tool_call>(.*?)</tool_call>", content or "", re.DOTALL)):
        block = match.group(1)
        arg_start = block.find("<arg_key>")
        if arg_start >= 0:
            name = block[:arg_start].strip()
            args_text = block[arg_start:]
        else:
            name = block.strip()
            args_text = ""
        arguments = {}
        for arg_match in re.finditer(
            r"<arg_key>(.*?)</arg_key>\s*<arg_value>(.*?)</arg_value>",
            args_text,
            re.DOTALL,
        ):
            key = arg_match.group(1).strip()
            value_text = arg_match.group(2).strip()
            try:
                value = json.loads(value_text)
            except json.JSONDecodeError:
                value = value_text
            arguments[key] = value
        if name:
            calls.append(
                {
                    "id": f"laguna_xml_call_{index}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(arguments, sort_keys=True),
                    },
                }
            )
    return calls


def message_from_chat_response(response):
    choice = response.choices[0]
    raw_message = choice.message
    if hasattr(raw_message, "model_dump"):
        data = raw_message.model_dump(mode="json", exclude_none=True)
    else:
        data = to_plain(raw_message)
    message = {"role": data.get("role") or "assistant"}
    content = data.get("content")
    if content is not None:
        message["content"] = content
    calls = structured_tool_calls(data)
    xml_calls = parse_laguna_xml_tool_calls(str(content or ""))
    if calls or xml_calls:
        message["tool_calls"] = calls or xml_calls
    return message


async def create_model_message(state, messages, client, tools):
    payload = {"model": model_name(state), "messages": messages, **sampling_args(state)}
    if tools:
        payload["tools"] = tools
    response = await client.chat.completions.create(**payload)
    return message_from_chat_response(response)


def local_command_for_tool(name, arguments):
    lowered = name.lower()
    if lowered in {"shell", "bash", "bash_command"}:
        command = arguments.get("command") or arguments.get("cmd") or arguments.get("keystrokes")
        return str(command or "")
    if lowered in {"cat", "read", "read_file"}:
        path = arguments.get("path") or arguments.get("file") or arguments.get("filename")
        if not path:
            return ""
        return "cat " + shlex.quote(str(path))
    if lowered == "keystrokes":
        value = str(arguments.get("keystrokes") or "")
        return value.strip()
    return None


async def run_local_command(command, cwd, timeout):
    if not command:
        return "Tool error: empty shell command."
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return f"Tool error: command timed out after {timeout}s."
    out = stdout.decode(errors="replace")
    err = stderr.decode(errors="replace")
    parts = [f"exit_code={process.returncode}"]
    if out:
        parts.append("stdout:\n" + out)
    if err:
        parts.append("stderr:\n" + err)
    return "\n".join(parts)


async def execute_tool(state, remote_tool_names, tool_call):
    function = tool_call["function"]
    name = function["name"]
    arguments = parse_json_args(function.get("arguments"))
    if name in remote_tool_names:
        return await call_remote_tool(state, name, arguments)
    if name.lower() == "done":
        state["stop_condition"] = "no_tools"
        return "done: " + str(arguments.get("reason") or "complete")
    command = local_command_for_tool(name, arguments)
    if command is None:
        return await call_remote_tool(state, name, arguments)
    cwd = os.environ.get("AGENT_WORKDIR") or "/app"
    timeout = int(os.environ.get("VF_TOOL_TIMEOUT", "900"))
    return await run_local_command(command, cwd, timeout)


async def main():
    state = json.loads(open(STATE_INPUT_PATH, encoding="utf-8").read())
    original_state = json.loads(json.dumps(state))
    state["sampling_args"] = sampling_args(state)
    tools, remote_tool_names, max_turns = load_tool_config()
    client = AsyncOpenAI(
        api_key=endpoint_token(),
        base_url=os.environ.get("OPENAI_BASE_URL") or state["endpoint_base_url"],
    )
    try:
        prompt_messages = [*(state.get("system_prompt") or []), *(state.get("prompt") or [])]
        messages = list(prompt_messages)
        state.setdefault("trajectory", [])
        trajectory_id = str(state.get("trajectory_id") or "")
        turn = 0
        while max_turns <= 0 or turn < max_turns:
            if await check_stop(state):
                break
            if record_prompt_size(state, messages) > prompt_token_budget():
                rollout_metrics(state)["overlong_prompt_count"] += 1
                state["stop_condition"] = "context_budget_exceeded"
                state["is_truncated"] = True
                break
            prompt = json.loads(json.dumps(messages))
            started = time.time()
            message = await create_model_message(state, messages, client, tools)
            ended = time.time()
            turn += 1
            completion = [message]
            messages.append(message)
            tool_calls = list(message.get("tool_calls") or [])
            if not tool_calls:
                state["stop_condition"] = "no_tools"
                state["trajectory"].append(
                    {
                        "prompt": prompt,
                        "completion": completion,
                        "response": {"message": message},
                        "tokens": None,
                        "reward": None,
                        "advantage": None,
                        "is_truncated": False,
                        "trajectory_id": trajectory_id,
                        "extras": {"laguna_xml_bridge": True, "model_elapsed_s": ended - started},
                    }
                )
                break
            for tool_call in tool_calls:
                try:
                    result = await execute_tool(state, remote_tool_names, tool_call)
                    content = compact_tool_observation(state, str(result))
                except Exception as exc:
                    content = compact_tool_observation(state, "Tool error: " + str(exc))
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": content,
                }
                completion.append(tool_message)
                messages.append(tool_message)
                if await check_stop(state):
                    break
            state["trajectory"].append(
                {
                    "prompt": prompt,
                    "completion": completion,
                    "response": {"message": message},
                    "tokens": None,
                    "reward": None,
                    "advantage": None,
                    "is_truncated": False,
                    "trajectory_id": trajectory_id,
                    "extras": {"laguna_xml_bridge": True, "model_elapsed_s": ended - started},
                }
            )
            if state.get("stop_condition"):
                break
        else:
            state["stop_condition"] = "max_turns_reached"
        state["completion"] = messages[len(prompt_messages):]
    finally:
        await client.close()
    patch = {
        key: value
        for key, value in state.items()
        if key not in original_state or original_state[key] != value
    }
    with open(STATE_OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(patch, handle)


asyncio.run(main())
"""


def harbor_success(state: vf.State) -> bool:
    metrics = state.get("metrics") or {}
    if isinstance(metrics, Mapping) and float(metrics.get("harbor_reward", 0.0) or 0.0) >= 1.0:
        return True
    tests = state.get("harbor_tests") or {}
    return isinstance(tests, Mapping) and int(tests.get("returncode", 1) or 1) == 0


def meta_control_rollout_metrics(state: vf.State) -> Mapping[str, Any]:
    metrics = state.get("meta_control_rollout_metrics") or {}
    return metrics if isinstance(metrics, Mapping) else {}


def checkpoint_outcomes(state: vf.State) -> list[str]:
    tests = state.get("harbor_tests") or {}
    if not isinstance(tests, Mapping):
        return []
    stdout = str(tests.get("stdout", "") or "")
    stderr = str(tests.get("stderr", "") or "")
    text = "\n".join(part for part in [stdout, stderr] if part)
    start_marker = "__ET_CHECKPOINTS__"
    end_marker = "__ET_CHECKPOINTS_END__"
    if start_marker not in text or end_marker not in text:
        return []
    payload = text.split(start_marker, 1)[1].split(end_marker, 1)[0].strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    rows = data.get("tests")
    if not isinstance(rows, list):
        return []
    outcomes: list[str] = []
    for row in rows:
        if isinstance(row, Mapping):
            outcomes.append(str(row.get("outcome", "notrun")))
    return outcomes


def checkpoint_prefix_share(state: vf.State) -> float:
    outcomes = checkpoint_outcomes(state)
    if not outcomes:
        return 0.0
    prefix = 0
    for outcome in outcomes:
        if outcome != "passed":
            break
        prefix += 1
    return float(prefix / len(outcomes))


def action_fingerprints(state: vf.State) -> list[str]:
    actions: list[str] = []
    trajectory = state.get("trajectory") or []
    if not isinstance(trajectory, list):
        return actions
    for step in trajectory:
        for call in iter_tool_calls(step):
            actions.append(stable_action_fingerprint(call))
    return actions


def action_observation_fingerprints(state: vf.State) -> list[str]:
    pairs: list[str] = []
    trajectory = state.get("trajectory") or []
    if not isinstance(trajectory, list):
        return pairs
    for step in trajectory:
        calls = [stable_action_fingerprint(call) for call in iter_tool_calls(step)]
        contents = list(iter_tool_message_content(step))
        for index, call in enumerate(calls):
            observation = contents[index] if index < len(contents) else ""
            pairs.append(f"{call}->{observation.strip()[:1000]}")
    return pairs


def tool_error_messages(state: vf.State) -> list[str]:
    errors: list[str] = []
    for content in iter_tool_message_content(state.get("trajectory") or []):
        lowered = content.lower()
        if any(marker in lowered for marker in ["traceback", "exception", "error:", "tool error", "keyerror", "valueerror"]):
            errors.append(content)
    return errors


def iter_tool_message_content(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        if value.get("role") == "tool" and "content" in value:
            yield str(value.get("content", ""))
        for item in value.values():
            yield from iter_tool_message_content(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_tool_message_content(item)


def iter_tool_calls(value: object) -> list[Mapping[str, Any]]:
    calls: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        if isinstance(value.get("completion"), list):
            calls.extend(iter_tool_calls(value["completion"]))
            return calls
        tool_calls = value.get("tool_calls")
        if isinstance(tool_calls, list):
            calls.extend(call for call in tool_calls if isinstance(call, Mapping))
        if not tool_calls and value.get("role") == "assistant" and isinstance(value.get("content"), str):
            calls.extend(parse_laguna_xml_tool_calls(str(value.get("content") or "")))
        if "name" in value and ("arguments" in value or "args" in value):
            calls.append(value)
        for key, item in value.items():
            if key == "tool_calls":
                continue
            if key == "function" and isinstance(value.get("function"), Mapping) and ("id" in value or "type" in value):
                continue
            calls.extend(iter_tool_calls(item))
    elif isinstance(value, list):
        for item in value:
            calls.extend(iter_tool_calls(item))
    return calls


def stable_action_fingerprint(call: Mapping[str, Any]) -> str:
    function = call.get("function")
    if isinstance(function, Mapping):
        name = function.get("name", call.get("name", ""))
        arguments = function.get("arguments", call.get("arguments", call.get("args", "")))
    else:
        name = call.get("name", "")
        arguments = call.get("arguments", call.get("args", ""))
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            parsed = arguments
        else:
            arguments = parsed
    try:
        normalized = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    except TypeError:
        normalized = str(arguments)
    return f"{name}:{normalized}"


class MetaControlEnvConfig(vf.EnvConfig):
    taskset: MetaControlTasksetConfig = MetaControlTasksetConfig()
    harness: MetaControlHarnessConfig = MetaControlHarnessConfig()


def load_taskset(config: MetaControlTasksetConfig) -> HarborTaskset:
    assert isinstance(config, MetaControlTasksetConfig)
    if config.dataset is None and config.bundle_package is None:
        config = config.model_copy(update={"bundle_package": __name__})
    return HarborTaskset(config=config)


def load_harness(config: MetaControlHarnessConfig) -> MetaControlHarness:
    assert isinstance(config, MetaControlHarnessConfig)
    return MetaControlHarness(config=config)


def coerce_env_config(config: vf.EnvConfig | Mapping[str, Any] | None) -> MetaControlEnvConfig:
    if config is None:
        return MetaControlEnvConfig()
    if isinstance(config, MetaControlEnvConfig):
        return config
    if isinstance(config, vf.EnvConfig):
        return MetaControlEnvConfig.model_validate(config.model_dump())
    if isinstance(config, Mapping):
        return MetaControlEnvConfig.model_validate(dict(config))
    raise TypeError(f"Unsupported config type: {type(config).__name__}")


def load_environment(config: vf.EnvConfig | Mapping[str, Any] | None = None, **kwargs: Any) -> vf.Env:
    raw_config: vf.EnvConfig | Mapping[str, Any] | None
    if kwargs:
        base = dict(config) if isinstance(config, Mapping) else {}
        raw_config = {**base, **kwargs}
    else:
        raw_config = config
    env_config = coerce_env_config(raw_config)
    return vf.Env(
        taskset=load_taskset(env_config.taskset),
        harness=load_harness(env_config.harness),
    )
