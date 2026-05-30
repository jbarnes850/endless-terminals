FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -e

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id user >/dev/null 2>&1; then
        useradd -m -s /bin/bash user
    fi

    WORKSPACE=/home/user/mlops_workspace
    EXPERIMENTS="$WORKSPACE/experiments"
    OLD_CACHE="$WORKSPACE/.du_cache"
    REPORTS="$WORKSPACE/reports"

    rm -rf "$WORKSPACE"
    mkdir -p "$EXPERIMENTS" "$OLD_CACHE" "$REPORTS"

    python3 <<'PY'
from pathlib import Path
import json

workspace = Path("/home/user/mlops_workspace")
experiments = workspace / "experiments"
old_cache = workspace / ".du_cache"

files = {
    "exp_alpha": {
        "checkpoints/model_epoch_001.ckpt": 16384,
        "checkpoints/model_epoch_002.ckpt": 24576,
        "checkpoints/export.onnx": 32768,
        "metrics.json": 512,
        "validation.metrics.json": 768,
        "history.csv": 1024,
        "logs/train.log": 4096,
        "logs/notes.txt": 2048,
        "images/confusion_matrix.png": 8192,
    },
    "exp_beta": {
        "weights/final.pt": 65536,
        "weights/final_ema.pth": 65536,
        "weights/best.ckpt": 49152,
        "metrics.json": 2048,
        "fold_0.csv": 4096,
        "fold_1.csv": 4096,
        "logs/run.log": 8192,
        "logs/debug.txt": 1024,
        "artifacts/sample_predictions.parquet": 32768,
        "artifacts/plot.png": 6144,
    },
    "exp_gamma": {
        "models/last.onnx": 40960,
        "models/teacher.pt": 57344,
        "metrics.json": 1024,
        "reports/eval.csv": 3072,
        "logs/train.log": 2048,
        "logs/eval.log": 2048,
        "tensorboard/events.out.tfevents.local": 12288,
        "README.txt": 1536,
    },
    "exp_delta": {
        "snapshot.ckpt": 32768,
        "metrics.json": 2048,
        "metrics.extra.csv": 2048,
        "logs/train.log": 1024,
        "logs/stdout.txt": 1024,
        "exports/model.onnx": 32768,
        "exports/model_quant.onnx": 28672,
        "cache/intermediate.bin": 16384,
    },
    "exp_epsilon": {
        "trial_a/checkpoint.pth": 20480,
        "trial_a/metrics.json": 1024,
        "trial_a/log.txt": 2048,
        "trial_b/checkpoint.pth": 22528,
        "trial_b/metrics.json": 1024,
        "trial_b/log.txt": 2048,
        "ensemble.onnx": 36864,
        "summary.csv": 4096,
    },
}

def write_sized_file(path: Path, size: int, seed: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pattern = (seed.encode("utf-8") + b"\n") or b"x"
    with path.open("wb") as f:
        remaining = size
        while remaining > 0:
            chunk = pattern[:remaining] if remaining < len(pattern) else pattern
            f.write(chunk)
            remaining -= len(chunk)

for exp_id, exp_files in files.items():
    for relpath, size in exp_files.items():
        write_sized_file(experiments / exp_id / relpath, size, f"{exp_id}:{relpath}")

old_inventory = """experiment_id\ttotal_bytes\tfile_count\tcheckpoint_count\tmetric_count\tlog_count\tlargest_file_bytes\tlargest_file_relpath
exp_beta\t237568\t9\t3\t2\t2\t65536\tweights/final.pt
exp_gamma\t119296\t8\t2\t2\t3\t57344\tmodels/teacher.pt
exp_delta\t116736\t8\t3\t2\t2\t32768\tsnapshot.ckpt
exp_alpha\t90368\t9\t3\t3\t2\t32768\tcheckpoints/export.onnx
exp_epsilon\t89088\t7\t3\t2\t2\t36864\tensemble.onnx
"""
(old_cache / "inventory.tsv").write_text(old_inventory, encoding="utf-8")

old_summary = {
    "schema_version": "artifact-index-v1",
    "source": "/home/user/mlops_workspace/experiments",
    "experiment_count": 5,
    "total_bytes": 653056,
    "total_files": 41,
    "largest_experiment": "exp_beta",
    "largest_experiment_bytes": 237568,
    "generated_by": "legacy-du-cache",
}
(old_cache / "summary.json").write_text(json.dumps(old_summary, indent=2) + "\n", encoding="utf-8")

(old_cache / "README.txt").write_text(
    "Legacy disk-usage cache retained for migration testing. This state is stale and not authoritative.\n",
    encoding="utf-8",
)
PY

    chown -R user:user /home/user/mlops_workspace
    chmod -R u+rwX,go+rX /home/user/mlops_workspace

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
