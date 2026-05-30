# Training Dependency Pin

This repo must use the repo-local Prime-RL checkout for Laguna meta-control
training compatibility probes:

```text
/Users/jarrodbarnes/endless-terminals/third_party/prime-rl
```

Current verified checkout:

- repository: `https://github.com/PrimeIntellect-ai/prime-rl.git`
- branch: `main`
- HEAD: `aeaf4c44f10365ff015a1a0e899dd3c6e1a5e7e1`
- upstream `origin/main`: `aeaf4c44f10365ff015a1a0e899dd3c6e1a5e7e1`
- describe: `v0.5.1.dev259`
- `pyproject.toml` version: `0.5.0`
- public submodules:
  - `deps/verifiers`: `43016ea6e4c47e946c37e93fe80dfe8c99892eef`
  - `deps/renderers`: `35c2407e9219e22d4da7e68fdb206d17b771120a`
  - `deps/pydantic-config`: `896ade4e69d8d8dff2d4b0a431b7e1c7c12d638f`
  - `deps/research-environments`: `c752781984c1b4fbb0a3d7f4aac1e7ed67cc749e`

Refresh command:

```bash
mkdir -p third_party
rm -rf third_party/prime-rl
git clone --filter=blob:none --depth=1 \
  https://github.com/PrimeIntellect-ai/prime-rl.git \
  third_party/prime-rl
git -C third_party/prime-rl config url.https://github.com/.insteadOf git@github.com:
git -C third_party/prime-rl submodule update --init --depth=1 \
  deps/verifiers \
  deps/renderers \
  deps/pydantic-config \
  deps/research-environments
```

Before any training launch, run:

```bash
python3 scripts/smoke_training_contracts.py \
  --prime-rl-root third_party/prime-rl \
  --json-out /tmp/laguna-meta-control-contracts.json
```

Do not use `/Users/jarrodbarnes/ai-scientist-training/prime-rl` or any other
external checkout for launch readiness. The version check must compare the
local `third_party/prime-rl` SHA against `origin/main` and fail if they differ.
The full Prime-RL uv dry-run should run on the Linux training node; the latest
workspace is CUDA/Linux constrained and local macOS dependency resolution is not
a reliable launch gate.

Important: Prime-RL version is not gate zero. The gate-zero contract is Laguna
XML execution through Verifiers:

```text
raw Laguna XML content
-> parsed tool call metadata
-> sandbox command execution
-> trajectory records action and observation
-> verifier/reward signal changes after state mutation
```

The executable contract is covered by:

```bash
uv run --project environments/meta_control \
  pytest environments/meta_control/tests/test_laguna_xml_harness.py
```
