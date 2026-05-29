#!/usr/bin/env bash
set -euo pipefail

rm -rf /workspace
mkdir -p /workspace
tar -xzf /tmp/endless_one_task.tgz -C /workspace

TASK="$(find /workspace -maxdepth 1 -type d -name 'task_*' | sort | head -1)"
if [[ -z "${TASK}" ]]; then
  echo "no task dir extracted" >&2
  exit 2
fi

sed \
  -e 's#Bootstrap: localimage#Bootstrap: docker#' \
  -e 's#From: ./ubuntu_22.04.sif#From: ubuntu:22.04#' \
  "${TASK}/container.def" > "${TASK}/container.prime.def"

apptainer build --force "${TASK}/container.sif" "${TASK}/container.prime.def"
apptainer exec \
  --containall \
  --writable-tmpfs \
  --cleanenv \
  --bind "${TASK}:/mnt" \
  "${TASK}/container.sif" \
  pytest -q /mnt/test_initial_state.py
