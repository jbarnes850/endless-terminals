from __future__ import annotations

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
