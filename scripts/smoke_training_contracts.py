#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
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


def find_renderer_root(explicit: Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.extend(Path("/Users/jarrodbarnes/.cache/uv/archive-v0").glob("*/renderers/base.py"))
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
    trainer = config.get("trainer") or {}

    require(orchestrator.get("rollouts_per_example") == 4, "orchestrator.rollouts_per_example must be 4")
    require(orchestrator.get("batch_size") == 4, "smoke batch_size must be exactly one n=4 group")
    require(orchestrator["batch_size"] % orchestrator["rollouts_per_example"] == 0, "batch_size must divide by n")
    require(orchestrator.get("max_concurrent", 0) >= 4, "max_concurrent must allow one full n=4 group")
    require(orchestrator.get("max_inflight_rollouts", 0) >= 4, "max_inflight_rollouts must allow one full n=4 group")
    require((orchestrator.get("env") or [{}])[0].get("id") == "meta-control", "orchestrator.env id must be meta-control")
    require(orchestrator.get("use_token_client") is False, "use_token_client must stay false until Laguna renderer TITO parity is proven")
    require((orchestrator.get("model") or {}).get("trust_remote_code") is True, "orchestrator tokenizer/model loading must trust Laguna remote code")
    require((orchestrator.get("buffer") or {}).get("online_difficulty_filtering") is True, "Prime-RL average-reward online filtering should be enabled as a weak native guard")

    wandb = config.get("wandb") or {}
    require(wandb.get("project"), "shared W&B project must be configured")
    require(wandb.get("shared") is True, "shared W&B mode must be enabled for trainer+orchestrator metrics")

    log_extras = ((orchestrator.get("wandb") or {}).get("log_extras") or {})
    require(log_extras.get("samples") is True, "orchestrator W&B sample logging must be enabled")
    require(log_extras.get("distributions") is True, "orchestrator W&B distribution logging must be enabled")
    require(log_extras.get("interval") == 1, "smoke must log samples/distributions every step")

    vllm_extra = inference.get("vllm_extra") or {}
    require(vllm_extra.get("renderer") == "laguna-xs.2", "inference.vllm_extra.renderer must be laguna-xs.2")
    require(vllm_extra.get("enable_thinking") is False, "Laguna renderer should run with enable_thinking=false")
    require((inference.get("parallel") or {}).get("tp") == 2, "smoke inference TP should use 2 GPUs")
    require((trainer.get("model") or {}).get("tp") == 2, "smoke trainer TP should use 2 GPUs")

    return {
        "rollouts_per_example": orchestrator["rollouts_per_example"],
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
        require(orchestrator.get("rollouts_per_example") == 16, f"{path}: rollouts_per_example must be 16")
        require(orchestrator.get("batch_size") == 64, f"{path}: batch_size must be 64")
        require(orchestrator["batch_size"] % orchestrator["rollouts_per_example"] == 0, f"{path}: batch_size must divide by n")
        require(orchestrator.get("max_concurrent", 0) >= 32, f"{path}: max_concurrent must be at least 32")
        require(orchestrator.get("max_inflight_rollouts", 0) >= 64, f"{path}: max_inflight_rollouts must be at least 64")
        require(advantage.get("type") == "default", f"{path}: default mean-baseline advantage must be explicit")
        require("length_shaping_alpha" not in advantage, f"{path}: length shaping must stay disabled")
        require(loss.get("type") == "default", f"{path}: use Prime-RL native default trainer loss")
        require(loss.get("teacher_tau", 0.0) == 0.0, f"{path}: no teacher KL in overnight sweep")
        require(log_extras.get("samples") is True, f"{path}: W&B sample logging must be enabled")
        require(log_extras.get("sample_ratio") == 1.0, f"{path}: sample_ratio=1.0 must log every rollout")
        checked[str(path)] = {
            "rollouts_per_example": orchestrator["rollouts_per_example"],
            "batch_size": orchestrator["batch_size"],
            "max_concurrent": orchestrator["max_concurrent"],
            "max_inflight_rollouts": orchestrator["max_inflight_rollouts"],
        }
    return checked


def check_prime_rl_contract(prime_root: Path) -> dict[str, Any]:
    orchestrator_py = prime_root / "src/prime_rl/orchestrator/orchestrator.py"
    advantage_py = prime_root / "src/prime_rl/orchestrator/advantage.py"
    vf_utils_py = prime_root / "src/prime_rl/orchestrator/vf_utils.py"
    scheduler_py = prime_root / "src/prime_rl/orchestrator/scheduler.py"
    server_py = prime_root / "src/prime_rl/inference/vllm/server.py"
    wandb_py = prime_root / "src/prime_rl/utils/monitor/wandb.py"

    for path in [orchestrator_py, advantage_py, vf_utils_py, scheduler_py, server_py, wandb_py]:
        require(path.exists(), f"missing Prime-RL source file: {path}")

    orchestrator = orchestrator_py.read_text()
    require(
        orchestrator.find('rewards = [r["reward"] for r in train_rollouts]') < orchestrator.find("compute_advantages("),
        "Prime-RL must compute advantages from rollout rewards after rollout scoring",
    )
    require(
        'metrics_df = pd.DataFrame([rollout["metrics"] for rollout in train_rollouts])' in orchestrator,
        "Prime-RL must surface rollout metrics into the logged metrics dataframe",
    )
    require('"rewards": rewards' in orchestrator and '"advantages": advantages' in orchestrator, "reward/advantage distributions must be loggable")

    vf_utils = vf_utils_py.read_text()
    require("group_inputs = [vf.RolloutInput(**example) for _ in range(rollouts_per_example)]" in vf_utils, "Verifiers group rollout must duplicate examples n times")
    require("state_columns = state_columns + REQUIRED_STATE_COLUMNS" in vf_utils, "Verifiers state columns must include required trajectory state")
    require('REQUIRED_STATE_COLUMNS = ["trajectory", "sampling_args"]' in vf_utils, "trajectory must be requested from Verifiers")

    scheduler = scheduler_py.read_text()
    require("rollouts_to_schedule=self.rollouts_per_example" in scheduler, "scheduler must schedule full rollout groups")
    require("await env_for_task.rubric.score_group" in scheduler, "scheduler must score completed groups before training batch use")

    server = server_py.read_text()
    require("for key, value in vllm_extra.items()" in server and "setattr(namespace, key, value)" in server, "Prime-RL inference must pass vllm_extra into vLLM namespace")

    wandb = wandb_py.read_text()
    require('self.samples_cols = ["step", "task", "example_id", "messages", "input_ids", "reward"]' in wandb, "W&B sample table must include rollout payload columns")
    require('wandb.log({"samples": self.samples_table, "step": step})' in wandb, "W&B sample logging must be wired")
    require("_select_rollout_samples" in orchestrator, "Prime-RL orchestrator must honor W&B sample_ratio for rollout sample logging")
    require("sample_ratio=1.0 logs every rollout" in orchestrator, "Prime-RL orchestrator must document all-rollout sample_ratio behavior")
    require("_log_rollouts_to_weave" in orchestrator and "WEAVE_PROJECT" in orchestrator, "Prime-RL orchestrator must log train rollouts to Weave when configured")

    return {
        "prime_rl_root": str(prime_root),
        "advantages_from_scored_rewards": True,
        "metrics_dataframe": True,
        "group_scoring_before_batch": True,
        "vllm_extra_runtime_hook": True,
        "wandb_samples": True,
        "weave_rollouts": True,
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
        "gated_progress",
        "stop_quality",
        "nonprogress_penalty",
        "malformed_tool_penalty",
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
    parser.add_argument("--prime-rl-root", type=Path, default=Path("/Users/jarrodbarnes/ai-scientist-training/prime-rl"))
    parser.add_argument("--env-dir", type=Path, default=Path("environments/meta_control"))
    parser.add_argument("--renderer-root", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=Path("/tmp/laguna-meta-control-contracts.json"))
    args = parser.parse_args()

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
