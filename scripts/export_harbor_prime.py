#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


def iter_tasks(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("task_"))


def toml_string(value: str) -> str:
    return json.dumps(value)


def toml_list(values: list[str]) -> str:
    return "[" + ", ".join(toml_string(v) for v in values) + "]"


def extract_post(def_text: str) -> str:
    match = re.search(r"(?ms)^%post\s*\n(.*?)(?=^%[A-Za-z]|\Z)", def_text)
    if not match:
        raise ValueError("container.def has no %post section")
    return match.group(1).rstrip() + "\n"


def make_dockerfile(def_text: str) -> str:
    post = extract_post(def_text)
    if "chmod -R a+rwX /home/user" not in post:
        post += "\nchmod -R a+rwX /home/user\n"
    marker = "__ENDLESS_DOCKER_POST__"
    return f"""FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'{marker}'
{post}{marker}
WORKDIR /home/user
"""


def write_task_toml(task: dict[str, Any], task_name: str, behavior: dict[str, Any] | None) -> str:
    keywords = ["endless-terminals", "terminal-bench-2", "agentic-rl"]
    if behavior:
        keywords.extend([str(behavior.get("capability", "")), str(behavior.get("id", ""))])
    keywords = sorted({k for k in keywords if k})
    description = str(task.get("description", "")).splitlines()[0][:240]
    metadata_lines = [
        'source = "endless-terminals"',
        'corpus = "behavior_trace_20260529_220"',
        'generation_mode = "behavior_conditioned_llm_funnel"',
    ]
    if behavior:
        metadata_lines.extend(
            [
                f"behavior_card_id = {toml_string(str(behavior.get('id', '')))}",
                f"capability = {toml_string(str(behavior.get('capability', '')))}",
                f"source_traces = {toml_list([str(x) for x in behavior.get('source_traces', [])])}",
            ]
        )
    return "\n".join(
        [
            'schema_version = "1.1"',
            "",
            "[task]",
            f"name = {toml_string('endless-terminals/' + task_name)}",
            f"description = {toml_string(description)}",
            'authors = [{ name = "Endless Terminals / Jarrod Barnes" }]',
            f"keywords = {toml_list(keywords)}",
            "",
            "[metadata]",
            *metadata_lines,
            "",
            "[verifier]",
            "timeout_sec = 300.0",
            'user = "root"',
            "",
            "[agent]",
            "timeout_sec = 900.0",
            'user = "user"',
            "",
            "[environment]",
            "build_timeout_sec = 900.0",
            'os = "linux"',
            "cpus = 2",
            "memory_mb = 4096",
            "storage_mb = 10240",
            "gpus = 0",
            "allow_internet = true",
            "",
        ]
    )


def export_one(task_dir: Path, out_root: Path) -> dict[str, Any]:
    task = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    metadata = task.get("metadata") or {}
    behavior = metadata.get("behavior_card") or {}
    out = out_root / task_dir.name
    if out.exists():
        shutil.rmtree(out)
    (out / "environment").mkdir(parents=True)
    (out / "tests").mkdir()
    (out / "solution").mkdir()

    (out / "instruction.md").write_text(str(task.get("description", "")).rstrip() + "\n", encoding="utf-8")
    (out / "task.toml").write_text(write_task_toml(task, task_dir.name, behavior), encoding="utf-8")
    dockerfile = make_dockerfile((task_dir / "container.def").read_text(encoding="utf-8"))
    (out / "environment" / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    shutil.copy2(task_dir / "test_final_state.py", out / "tests" / "test_final_state.py")
    (out / "tests" / "test.sh").write_text(
        """#!/bin/bash
set +e
mkdir -p /logs/verifier
cd /home/user
python3 -m pytest -q /tests/test_final_state.py
rc=$?
if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
""",
        encoding="utf-8",
    )
    (out / "tests" / "test.sh").chmod(0o755)
    (out / "solution" / "solve.sh").write_text(
        "#!/bin/bash\n# Oracle solution intentionally omitted for RL/eval packaging.\nexit 1\n",
        encoding="utf-8",
    )
    (out / "solution" / "solve.sh").chmod(0o755)
    return {
        "source_task_dir": str(task_dir),
        "harbor_task_dir": str(out),
        "task_name": f"endless-terminals/{task_dir.name}",
        "behavior_card_id": behavior.get("id"),
        "capability": behavior.get("capability"),
    }


def write_prime_environment(env_dir: Path, package_name: str) -> None:
    if env_dir.exists():
        shutil.rmtree(env_dir)
    env_dir.mkdir(parents=True)
    (env_dir / package_name).mkdir()
    (env_dir / package_name / "__init__.py").write_text(
        "from .environment import load_environment, load_taskset\n",
        encoding="utf-8",
    )
    (env_dir / package_name / "environment.py").write_text(
        '''from __future__ import annotations

import verifiers as vf
from tasksets import HarborTaskset, HarborTasksetConfig


class EndlessBehaviorTasksetConfig(HarborTasksetConfig):
    split: str = "train"


def load_taskset(config: EndlessBehaviorTasksetConfig | None = None):
    config = config or EndlessBehaviorTasksetConfig(bundle_package=__name__)
    if not getattr(config, "bundle_package", None):
        config.bundle_package = __name__
    return HarborTaskset(config=config)


def load_environment(config: vf.EnvConfig | None = None) -> vf.Env:
    from harnesses import OpenCode, OpenCodeConfig

    taskset_config = None
    harness_config = None
    if config is not None:
        taskset_config = config.taskset
        harness_config = config.harness
    taskset = load_taskset(taskset_config)
    harness = OpenCode(config=harness_config or OpenCodeConfig())
    return vf.Env(taskset=taskset, harness=harness)
''',
        encoding="utf-8",
    )
    (env_dir / "pyproject.toml").write_text(
        f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "endless-behavior-trace"
version = "0.1.0"
description = "Behavior-conditioned Endless Terminals Harbor taskset for Prime Verifiers"
requires-python = ">=3.10,<3.14"
dependencies = [
  "verifiers @ git+https://github.com/PrimeIntellect-ai/verifiers.git",
  "harnesses @ git+https://github.com/PrimeIntellect-ai/verifiers.git#subdirectory=packages/harnesses",
  "tasksets[openenv,openreward,ta] @ git+https://github.com/PrimeIntellect-ai/verifiers.git#subdirectory=packages/tasksets",
]

[tool.hatch.build.targets.wheel]
packages = ["{package_name}"]
artifacts = ["{package_name}/tasks/**"]

[tool.hatch.metadata]
allow-direct-references = true
''',
        encoding="utf-8",
    )
    (env_dir / "README.md").write_text(
        """# Endless Behavior Trace

Prime Verifiers wrapper for the behavior-conditioned Endless Terminals Harbor corpus.

Local smoke:

```bash
uv run vf-build endless-behavior-trace
prime eval run endless-behavior-trace -m openai/gpt-5-nano
```
""",
        encoding="utf-8",
    )


def copy_prime_tasks(harbor_out: Path, env_dir: Path, package_name: str, rows: list[dict[str, Any]]) -> None:
    tasks_out = env_dir / package_name / "tasks"
    if tasks_out.exists():
        shutil.rmtree(tasks_out)
    tasks_out.mkdir(parents=True)
    for row in rows:
        src = Path(row["harbor_task_dir"])
        dst = tasks_out / src.name
        shutil.copytree(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export generated Endless tasks to Harbor and Prime Verifiers format.")
    parser.add_argument("--tasks-dir", required=True)
    parser.add_argument("--harbor-out", required=True)
    parser.add_argument("--prime-env-out", required=True)
    parser.add_argument("--eligible-file", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    tasks_dir = Path(args.tasks_dir).resolve()
    harbor_out = Path(args.harbor_out).resolve()
    prime_env_out = Path(args.prime_env_out).resolve()
    write_prime_environment(prime_env_out, "endless_behavior_trace")
    harbor_out.mkdir(parents=True, exist_ok=True)

    eligible: set[str] | None = None
    if args.eligible_file:
        eligible = set()
        for line in Path(args.eligible_file).read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if text:
                eligible.add(Path(text).name)

    rows = []
    skipped = []
    for task_dir in iter_tasks(tasks_dir)[: args.limit]:
        if eligible is not None and task_dir.name not in eligible:
            skipped.append(
                {
                    "source_task_dir": str(task_dir),
                    "task": task_dir.name,
                    "reason": "not_build_initial_pass_eligible",
                }
            )
            continue
        try:
            rows.append(export_one(task_dir, harbor_out))
        except Exception as exc:
            partial = harbor_out / task_dir.name
            if partial.exists():
                shutil.rmtree(partial)
            skipped.append(
                {
                    "source_task_dir": str(task_dir),
                    "task": task_dir.name,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
    manifest = {
        "source_tasks_dir": str(tasks_dir),
        "harbor_tasks_dir": str(harbor_out),
        "prime_env_dir": str(prime_env_out),
        "num_tasks": len(rows),
        "num_skipped": len(skipped),
        "rows": rows,
        "skipped": skipped,
    }
    (harbor_out.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    copy_prime_tasks(harbor_out, prime_env_out, "endless_behavior_trace", rows)
    (prime_env_out / "endless_behavior_trace" / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({k: manifest[k] for k in ("harbor_tasks_dir", "prime_env_dir", "num_tasks", "num_skipped")}, indent=2))


if __name__ == "__main__":
    main()
