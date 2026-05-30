#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import subprocess
import statistics
import sys
import tomllib
from pathlib import Path
from typing import Any


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def default_prime_rl_root() -> Path | None:
    repo_local = Path("third_party/prime-rl")
    if repo_local.exists():
        return repo_local
    if os.environ.get("PRIME_RL_ROOT"):
        return Path(os.environ["PRIME_RL_ROOT"])
    return None


def git_output(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()


def find_renderer_root(explicit: Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    renderer_env = os.environ.get("RENDERERS_ROOT")
    if renderer_env:
        candidates.append(Path(renderer_env))
    spec = importlib.util.find_spec("renderers")
    if spec and spec.submodule_search_locations:
        candidates.append(Path(next(iter(spec.submodule_search_locations))))
    candidates.extend(Path("/Users/jarrodbarnes/.cache/uv/archive-v0").glob("*/renderers/base.py"))
    candidates.extend(Path("/workspace/.cache/uv/archive-v0").glob("*/renderers/base.py"))
    for candidate in candidates:
        root = candidate if candidate.name == "renderers" else candidate.parent
        if (
            (root / "base.py").exists()
            and (root / "configs.py").exists()
            and (root / "laguna_xs2.py").exists()
            and (root / "parsing.py").exists()
        ):
            return root
    fail("could not find PrimeIntellect renderers package with laguna_xs2.py")


def check_config(config: dict[str, Any]) -> dict[str, Any]:
    orchestrator = config.get("orchestrator") or {}
    inference = config.get("inference") or {}
    require(orchestrator.get("group_size") == 4, "orchestrator.group_size must be 4")
    require(orchestrator.get("batch_size") == 4, "smoke batch_size must be exactly one n=4 group")
    require(orchestrator["batch_size"] % orchestrator["group_size"] == 0, "batch_size must divide by n")
    require(orchestrator.get("max_inflight_rollouts", 0) >= 4, "max_inflight_rollouts must allow one full n=4 group")
    train = orchestrator.get("train") or {}
    require((train.get("env") or [{}])[0].get("id") == "meta-control", "orchestrator.train.env id must be meta-control")
    require(train.get("num_workers", 0) >= 4, "smoke train.num_workers must allow one full n=4 group")
    require((orchestrator.get("model") or {}).get("trust_remote_code") is True, "orchestrator tokenizer/model loading must trust Laguna remote code")
    require((orchestrator.get("buffer") or {}).get("online_difficulty_filtering") is True, "Prime-RL average-reward online filtering should be enabled as a weak native guard")

    wandb = config.get("wandb") or {}
    require(wandb.get("project"), "shared W&B project must be configured")
    require(wandb.get("offline") is False, "W&B must be online for trainer+orchestrator metrics")

    log_extras = ((orchestrator.get("wandb") or {}).get("log_extras") or {})
    require(log_extras.get("samples") is True, "orchestrator W&B sample logging must be enabled")
    require(log_extras.get("distributions") is True, "orchestrator W&B distribution logging must be enabled")
    require(log_extras.get("interval") == 1, "smoke must log samples/distributions every step")

    vllm_extra = inference.get("vllm_extra") or {}
    require(vllm_extra.get("renderer") == "laguna-xs.2", "inference.vllm_extra.renderer must be laguna-xs.2")
    require(vllm_extra.get("enable_thinking") is False, "Laguna renderer should run with enable_thinking=false")
    require((inference.get("parallel") or {}).get("tp") == 2, "smoke inference TP should use 2 GPUs")
    trainer_model = ((config.get("trainer") or {}).get("model") or {})
    trainer_has_lora = (trainer_model.get("lora") or {}).get("rank") is not None
    require(
        inference.get("enable_lora") is trainer_has_lora,
        "inference LoRA must match trainer.model.lora so online adapter sync is exercised when LoRA training is enabled",
    )

    return {
        "group_size": orchestrator["group_size"],
        "batch_size": orchestrator["batch_size"],
        "wandb_project": wandb["project"],
        "renderer": vllm_extra["renderer"],
    }


def check_scale_configs(paths: list[Path]) -> dict[str, Any]:
    checked: dict[str, Any] = {}
    for path in paths:
        config = load_toml(path)
        orchestrator = config.get("orchestrator") or {}
        advantage = orchestrator.get("advantage") or {}
        log_extras = ((orchestrator.get("wandb") or {}).get("log_extras") or {})
        loss = ((config.get("trainer") or {}).get("loss") or {})
        trainer_model = ((config.get("trainer") or {}).get("model") or {})
        inference = config.get("inference") or {}
        train = orchestrator.get("train") or {}
        require(orchestrator.get("group_size") == 8, f"{path}: group_size must be 8")
        require(orchestrator.get("batch_size") == 8, f"{path}: batch_size must be one n=8 group for long-horizon terminal rollouts")
        require(orchestrator["batch_size"] % orchestrator["group_size"] == 0, f"{path}: batch_size must divide by n")
        require(orchestrator.get("max_inflight_rollouts", 0) == 8, f"{path}: max_inflight_rollouts must match the n=8 tunnel-safe group")
        require(orchestrator.get("tasks_per_minute") == 6, f"{path}: tasks_per_minute must rate-limit sandbox tunnel creation")
        envs = train.get("env") or []
        require(envs and envs[0].get("id") == "meta-control", f"{path}: meta_control train env must be configured")
        require(train.get("num_workers") == 8, f"{path}: train.num_workers must match the n=8 rollout group")
        require(advantage.get("type") == "default", f"{path}: default mean-baseline advantage must be explicit")
        require("length_shaping_alpha" not in advantage, f"{path}: length shaping must stay disabled")
        require(loss.get("type") == "default", f"{path}: use Prime-RL native default trainer loss")
        require("teacher_tau" not in loss, f"{path}: no teacher KL in overnight sweep")
        require((trainer_model.get("ac") or {}).get("freq") == 1, f"{path}: full activation checkpointing required for Laguna full-policy training")
        require((trainer_model.get("ac_offloading") or {}).get("max_inflight_activations") == 1, f"{path}: activation offloading required after full-policy OOM at seq_len=8192")
        require(trainer_model.get("optim_cpu_offload") is True, f"{path}: optimizer CPU offload required for Laguna full-policy training on 4xA100 trainer shard")
        require(trainer_model.get("seq_len") == 4096, f"{path}: trainer seq_len must stay at 4096 unless a larger smoke passes")
        require((trainer_model.get("lora") or {}).get("rank") == 16, f"{path}: LoRA rank 16 required after full-policy OOM on 4xA100 trainer shard")
        require(((config.get("orchestrator") or {}).get("model") or {}).get("lora") is not None, f"{path}: orchestrator model must declare LoRA for online adapter sync")
        require(inference.get("enable_lora") is True, f"{path}: inference LoRA must be enabled for online adapter sync")
        require(log_extras.get("samples") is True, f"{path}: W&B sample logging must be enabled")
        require(log_extras.get("sample_ratio") == 1.0, f"{path}: sample_ratio=1.0 must log every rollout")
        checked[str(path)] = {
            "group_size": orchestrator["group_size"],
            "batch_size": orchestrator["batch_size"],
            "max_inflight_rollouts": orchestrator["max_inflight_rollouts"],
            "train_num_workers": train.get("num_workers"),
            "activation_checkpoint_freq": (trainer_model.get("ac") or {}).get("freq"),
            "optim_cpu_offload": trainer_model.get("optim_cpu_offload"),
        }
    return checked


def check_prime_rl_contract(prime_root: Path) -> dict[str, Any]:
    pyproject = prime_root / "pyproject.toml"
    config_py = prime_root / "packages/prime-rl-configs/src/prime_rl/configs/orchestrator.py"
    orchestrator_py = prime_root / "src/prime_rl/orchestrator/orchestrator.py"
    advantage_py = prime_root / "src/prime_rl/orchestrator/advantage.py"
    envs_py = prime_root / "src/prime_rl/orchestrator/envs.py"
    scheduler_py = prime_root / "src/prime_rl/orchestrator/scheduler.py"
    server_py = prime_root / "src/prime_rl/inference/vllm/server.py"
    wandb_py = prime_root / "src/prime_rl/utils/monitor/wandb.py"
    laguna_model_py = prime_root / "src/prime_rl/trainer/models/laguna/modeling_laguna.py"
    laguna_convert_py = prime_root / "src/prime_rl/trainer/models/laguna/converting_laguna.py"

    for path in [
        pyproject,
        config_py,
        orchestrator_py,
        advantage_py,
        envs_py,
        scheduler_py,
        server_py,
        wandb_py,
        laguna_model_py,
        laguna_convert_py,
    ]:
        require(path.exists(), f"missing Prime-RL source file: {path}")

    head = git_output(prime_root, "rev-parse", "HEAD")
    branch = git_output(prime_root, "branch", "--show-current")
    describe = git_output(prime_root, "describe", "--tags", "--always", "--dirty")
    remote_main = git_output(prime_root, "ls-remote", "origin", "refs/heads/main").split()[0]
    require(head == remote_main, f"Prime-RL checkout is not current origin/main: {head} != {remote_main}")
    require(branch == "main", f"Prime-RL checkout must be on main, got {branch!r}")
    require("dirty" not in describe, f"Prime-RL checkout must be clean for compatibility probe, got {describe}")

    config_model = config_py.read_text()
    require(
        'group_size: int = Field(1, ge=1, validation_alias=AliasChoices("group_size", "rollouts_per_example"))'
        in config_model,
        "Prime-RL config model must prove group_size is canonical and rollouts_per_example is only a validation alias",
    )

    orchestrator = orchestrator_py.read_text()
    require(
        orchestrator.find("num_rollouts = len(train_rollouts)") < orchestrator.find("compute_advantages, train_rollouts, config.advantage"),
        "Prime-RL must compute advantages from rollout rewards after rollout scoring",
    )
    require(
        'metrics_df = pd.DataFrame([rollout["metrics"] for rollout in train_rollouts])' in orchestrator,
        "Prime-RL must surface rollout metrics into the logged metrics dataframe",
    )
    require('"advantages": [r["advantage"] for r in train_rollouts]' in orchestrator, "advantage distributions must be loggable")

    envs = envs_py.read_text()
    require("REQUIRED_STATE_COLUMNS = [\"trajectory\", \"sampling_args\"]" in envs, "trajectory must be requested from Verifiers")
    require("[vf.RolloutInput(**example) for _ in range(group_size)]" in envs, "Verifiers group rollout must duplicate examples n times")
    require("state_columns=self.state_columns" in envs, "Verifiers rollout object must expose requested trajectory state")

    scheduler = scheduler_py.read_text()
    require("self.group_size = config.group_size" in scheduler, "scheduler must use canonical group_size")
    require("rollouts_to_schedule=self.group_size" in scheduler, "scheduler must schedule full rollout groups")
    require("env.run_group(" in scheduler and "group_size=rollout_count" in scheduler, "scheduler must preserve group scoring path")
    require("self.buffer.update(completed_rollouts)" in scheduler, "scheduler must score and buffer completed rollouts before training batch use")

    server = server_py.read_text()
    require("for key, value in vllm_extra.items()" in server and "setattr(namespace, key, value)" in server, "Prime-RL inference must pass vllm_extra into vLLM namespace")
    laguna_model = laguna_model_py.read_text()
    laguna_convert = laguna_convert_py.read_text()
    require(
        "class LagunaForCausalLM" in laguna_model and "LagunaConfig" in laguna_model,
        "Prime-RL trainer must include a native Laguna model implementation",
    )
    require(
        "mlp.experts.e_score_correction_bias" in laguna_convert
        and "mlp.gate.e_score_correction_bias" in laguna_convert
        and "mlp.shared_expert" in laguna_convert
        and "mlp.shared_experts" in laguna_convert,
        "Prime-RL Laguna conversion must handle router correction bias and shared expert key variants",
    )

    wandb = wandb_py.read_text()
    require('self.samples_cols = ["step", "env_name", "task", "example_id", "messages", "input_ids", "reward"]' in wandb, "W&B sample table must include rollout payload columns")
    require('wandb.log({"samples": self.samples_table, "step": step})' in wandb, "W&B sample logging must be wired")
    require("sample_items_for_logging" in wandb and "self.config.log_extras.sample_ratio" in wandb, "W&B sample_ratio must be honored")

    return {
        "prime_rl_root": str(prime_root),
        "head": head,
        "describe": describe,
        "advantages_from_scored_rewards": True,
        "metrics_dataframe": True,
        "group_scoring_before_batch": True,
        "laguna_native_trainer": True,
        "vllm_extra_runtime_hook": True,
        "wandb_samples": True,
        "weave_native": False,
    }


def check_renderer_contract(renderer_root: Path) -> dict[str, Any]:
    base = (renderer_root / "base.py").read_text()
    configs = (renderer_root / "configs.py").read_text()
    laguna = (renderer_root / "laguna_xs2.py").read_text()
    parsing = (renderer_root / "parsing.py").read_text()

    require('"poolside/Laguna-XS.2": "laguna-xs.2"' in base, "renderer map must bind poolside/Laguna-XS.2 to laguna-xs.2")
    require('"laguna-xs.2": LagunaXS2Renderer' in base, "renderer registry must expose LagunaXS2Renderer")
    require('name: Literal["laguna-xs.2"] = "laguna-xs.2"' in configs, "LagunaXS2RendererConfig discriminator missing")
    require("enable_thinking: bool = False" in configs, "LagunaXS2RendererConfig must default enable_thinking=false")
    require("<tool_call>" in laguna and "<arg_key>" in laguna and "<arg_value>" in laguna, "Laguna renderer must use native XML-ish tool calls")
    require("def parse_laguna_xs2" in parsing, "Laguna parser must exist")

    return {
        "renderer_root": str(renderer_root),
        "model_map": "poolside/Laguna-XS.2 -> laguna-xs.2",
        "enable_thinking_default": False,
        "native_tool_format": True,
    }


def parse_metric_names(environment_py: Path) -> list[str]:
    tree = ast.parse(environment_py.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute) and decorator.attr in {"metric", "reward"}:
                    names.append(node.name)
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr in {"metric", "reward"}:
                    names.append(node.name)
    return sorted(set(names))


def check_verifiers_contract(env_dir: Path) -> dict[str, Any]:
    env_py = env_dir / "meta_control/environment.py"
    manifest = env_dir / "meta_control/manifest.json"
    require(env_py.exists(), f"missing environment.py: {env_py}")
    require(manifest.exists(), f"missing manifest: {manifest}")
    manifest_data = json.loads(manifest.read_text())
    require(manifest_data.get("num_tasks", 0) > 0, "environment manifest must contain tasks")

    text = env_py.read_text()
    for required in [
        "tool_call_count",
        "unique_action_count",
        "adjacent_repeat_count",
        "dominant_action_share",
        "unchanged_state_rate",
        "natural_stop",
        "max_turn_stop",
        "checkpoint_count",
        "checkpoint_prefix_share",
        "tool_error_count",
        "raw_observation_tokens",
        "compacted_observation_tokens",
        "truncated_bytes",
        "overlong_prompt_count",
        "max_prompt_estimated_tokens",
        "gated_progress",
        "stop_quality",
        "nonprogress_penalty",
        "malformed_tool_penalty",
        "context_budget_penalty",
        "turn_cost",
        "reward_group_std",
        "low_reward_variance_group",
    ]:
        require(required in text, f"Verifiers wrapper missing metric/reward: {required}")
    require('state.get("stop_condition")' in text, "stop_condition must be read from rollout state")
    require('state.get("trajectory")' in text, "trajectory must be read for tool/action fingerprints")
    require("tool_calls" in text, "tool_calls must be extracted from trajectory")
    require("__ET_CHECKPOINTS__" in text, "checkpoint parser must consume hidden verifier checkpoint marker")

    test_scripts = sorted((env_dir / "meta_control/tasks").glob("*/tests/test.sh"))
    require(test_scripts, "environment must package Harbor test scripts")
    for script in test_scripts[:3]:
        script_text = script.read_text()
        require("-p et_checkpoint_plugin" in script_text, f"test script must emit checkpoint metadata: {script}")
        require("__ET_CHECKPOINTS__" in script_text, f"test script missing checkpoint marker: {script}")

    synthetic_rewards = [0.0, 1.0, 0.0, 1.0]
    reward_group_std = statistics.pstdev(synthetic_rewards)
    require(reward_group_std > 1e-5, "synthetic mixed-success n=4 group must have nonzero reward std")

    return {
        "env_dir": str(env_dir),
        "num_tasks": manifest_data["num_tasks"],
        "metrics": parse_metric_names(env_py),
        "synthetic_reward_group_std": reward_group_std,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-check Laguna meta-control Prime-RL training contracts.")
    parser.add_argument("--config", type=Path, default=Path("training/configs/meta_control_smoke.toml"))
    parser.add_argument(
        "--prime-rl-root",
        type=Path,
        default=default_prime_rl_root(),
    )
    parser.add_argument("--env-dir", type=Path, default=Path("environments/meta_control"))
    parser.add_argument("--renderer-root", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=Path("/tmp/laguna-meta-control-contracts.json"))
    args = parser.parse_args()

    if args.prime_rl_root is None:
        raise SystemExit("FAIL: pass --prime-rl-root or check out Prime-RL at third_party/prime-rl.")

    config = load_toml(args.config)
    report = {
        "config": check_config(config),
        "scale_configs": check_scale_configs(
            [
                Path("training/configs/meta_control_A_baseline_gated.toml"),
                Path("training/configs/meta_control_B_anti_inertia.toml"),
                Path("training/configs/meta_control_C_stop_verification.toml"),
            ]
        ),
        "prime_rl": check_prime_rl_contract(args.prime_rl_root),
        "verifiers_env": check_verifiers_contract(args.env_dir),
        "renderer": check_renderer_contract(find_renderer_root(args.renderer_root)),
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
