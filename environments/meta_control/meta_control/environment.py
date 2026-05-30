from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
import statistics
from typing import Any

import verifiers as vf
from tasksets import HarborTaskset, HarborTasksetConfig


class MetaControlTasksetConfig(HarborTasksetConfig):
    bundle_package: str | None = __name__


class MetaControlHarnessConfig(vf.HarnessConfig):
    # Native Verifiers base program: Prime-RL samples Laguna through the
    # laguna-xs.2 renderer, then Verifiers executes model tool calls inside the
    # task sandbox and Harbor scores the hidden final verifier.
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
    turn_cost_unit: float = 0.005
    turn_cost_cap: float = 0.02
    success_turn_cost_cap: float = 0.01


class MetaControlHarness(vf.Harness[MetaControlHarnessConfig]):
    config: MetaControlHarnessConfig

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


def harbor_success(state: vf.State) -> bool:
    metrics = state.get("metrics") or {}
    if isinstance(metrics, Mapping) and float(metrics.get("harbor_reward", 0.0) or 0.0) >= 1.0:
        return True
    tests = state.get("harbor_tests") or {}
    return isinstance(tests, Mapping) and int(tests.get("returncode", 1) or 1) == 0


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
        tool_calls = value.get("tool_calls")
        if isinstance(tool_calls, list):
            calls.extend(call for call in tool_calls if isinstance(call, Mapping))
        if "name" in value and ("arguments" in value or "args" in value):
            calls.append(value)
        for item in value.values():
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
