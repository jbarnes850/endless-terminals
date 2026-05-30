#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


def iter_tasks(roots: list[Path]) -> list[Path]:
    tasks: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        for path in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("task_")):
            if path.name in seen:
                continue
            seen.add(path.name)
            tasks.append(path)
    return tasks


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
cat > /tmp/et_checkpoint_plugin.py <<'PY'
import json
import os

_items = []
_outcomes = {}


def pytest_collection_modifyitems(session, config, items):
    global _items
    _items = [item.nodeid for item in items]


def pytest_runtest_logreport(report):
    if report.when not in ("setup", "call", "teardown"):
        return
    current = _outcomes.get(report.nodeid)
    if current == "failed":
        return
    if report.failed:
        _outcomes[report.nodeid] = "failed"
    elif report.skipped and current is None:
        _outcomes[report.nodeid] = "skipped"
    elif report.when == "call" and report.passed and current is None:
        _outcomes[report.nodeid] = "passed"


def pytest_sessionfinish(session, exitstatus):
    os.makedirs("/logs/verifier", exist_ok=True)
    tests = [
        {"nodeid": nodeid, "outcome": _outcomes.get(nodeid, "notrun")}
        for nodeid in _items
    ]
    with open("/logs/verifier/checkpoints.json", "w", encoding="utf-8") as handle:
        json.dump({"exitstatus": int(exitstatus), "tests": tests}, handle, sort_keys=True)
PY
PYTHONPATH=/tmp python3 -m pytest -q -p et_checkpoint_plugin /tests/test_final_state.py
rc=$?
printf '\\n__ET_CHECKPOINTS__\\n'
cat /logs/verifier/checkpoints.json 2>/dev/null || true
printf '\\n__ET_CHECKPOINTS_END__\\n'
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
    template_path = (
        Path(__file__).resolve().parents[1]
        / "environments"
        / "meta_control"
        / "meta_control"
        / "environment.py"
    )
    environment_template = template_path.read_text(encoding="utf-8")
    if env_dir.exists():
        shutil.rmtree(env_dir)
    env_dir.mkdir(parents=True)
    (env_dir / package_name).mkdir()
    (env_dir / package_name / "__init__.py").write_text(
        """from .environment import (
    MetaControlHarness,
    coerce_env_config,
    load_environment,
    load_harness,
    load_taskset,
)
""",
        encoding="utf-8",
    )
    (env_dir / package_name / "environment.py").write_text(environment_template, encoding="utf-8")
    (env_dir / "pyproject.toml").write_text(
        f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "meta-control"
version = "0.1.0"
description = "Behavior-conditioned Endless Terminals Harbor taskset for Prime Verifiers"
requires-python = ">=3.10,<3.14"
dependencies = [
  "verifiers @ git+https://github.com/PrimeIntellect-ai/verifiers.git@82310b9c049b39d1eacb14c7c2b2ce0e76469899",
  "tasksets[openenv,openreward,ta] @ git+https://github.com/PrimeIntellect-ai/verifiers.git@82310b9c049b39d1eacb14c7c2b2ce0e76469899#subdirectory=packages/tasksets",
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
        """# Meta Control

Prime Verifiers wrapper for the behavior-conditioned Endless Terminals Harbor corpus.

This package bundles an executable-admitted Endless Terminals subset selected by the provided eligible file. For training exports, that eligible file should be the calibrated Laguna pass-band task list, after GPT-5.5 reference pruning on Laguna-zero tasks.

Local smoke:

```bash
uv build
prime --plain env install meta-control -p environments --no-upgrade
uv run python - <<'PY'
import verifiers as vf
env = vf.load_environment("meta-control")
print(type(env.harness).__name__, len(env.taskset.load_tasks()))
PY
```

For Prime-RL training with Laguna, use the `laguna-xs.2` renderer.
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


def read_executable_tasks(path: Path) -> set[str]:
    report = json.loads(path.read_text(encoding="utf-8"))
    return {
        Path(row["task_dir"]).resolve().name
        for row in report.get("rows", [])
        if (
            row.get("executable_ok")
            or row.get("calibration_eligible")
            or (row.get("build_ok") and row.get("initial_tests_ok"))
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export generated Endless tasks to Harbor and Prime Verifiers format.")
    parser.add_argument("--tasks-dir", required=True, action="append")
    parser.add_argument("--harbor-out", required=True)
    parser.add_argument("--prime-env-out", required=True)
    parser.add_argument("--eligible-file", required=True)
    parser.add_argument("--admission-report", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    tasks_dirs = [Path(path).resolve() for path in args.tasks_dir]
    harbor_out = Path(args.harbor_out).resolve()
    prime_env_out = Path(args.prime_env_out).resolve()
    write_prime_environment(prime_env_out, "meta_control")
    harbor_out.mkdir(parents=True, exist_ok=True)

    executable = read_executable_tasks(Path(args.admission_report))
    eligible: set[str] = set()
    for line in Path(args.eligible_file).read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text:
            eligible.add(Path(text).name)
    ineligible = sorted(eligible - executable)
    if ineligible:
        preview = ", ".join(ineligible[:20])
        extra = "" if len(ineligible) <= 20 else f", ... ({len(ineligible)} total)"
        raise SystemExit(
            "Eligible file contains tasks that did not pass executable-environment admission: "
            f"{preview}{extra}"
        )

    rows = []
    skipped = []
    for task_dir in iter_tasks(tasks_dirs)[: args.limit]:
        if task_dir.name not in eligible:
            skipped.append(
                {
                    "source_task_dir": str(task_dir),
                    "task": task_dir.name,
                    "reason": "not_executable_environment_admitted",
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
        "source_tasks_dirs": [str(path) for path in tasks_dirs],
        "harbor_tasks_dir": str(harbor_out),
        "prime_env_dir": str(prime_env_out),
        "num_tasks": len(rows),
        "num_skipped": len(skipped),
        "rows": rows,
        "skipped": skipped,
    }
    (harbor_out.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    copy_prime_tasks(harbor_out, prime_env_out, "meta_control", rows)
    (prime_env_out / "meta_control" / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({k: manifest[k] for k in ("harbor_tasks_dir", "prime_env_dir", "num_tasks", "num_skipped")}, indent=2))


if __name__ == "__main__":
    main()
