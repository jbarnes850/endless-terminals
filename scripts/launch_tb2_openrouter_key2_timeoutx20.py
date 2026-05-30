#!/usr/bin/env python3
"""Launch the slow OpenRouter Laguna TB2 fallback without printing secrets."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


KEY_FILE = Path("/Users/jarrodbarnes/sci-feasibility/.env")
KEY_NAME = "OPENROUTER_API_KEY"


def load_key() -> str:
    for line in KEY_FILE.read_text(errors="ignore").splitlines():
        match = re.match(rf"^\s*{KEY_NAME}\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise SystemExit(f"{KEY_NAME} not found in {KEY_FILE}")


def main() -> int:
    env = os.environ.copy()
    env[KEY_NAME] = load_key()
    command = [
        "uv",
        "run",
        "--extra",
        "harbor",
        "python",
        "scripts/run_tb2_laguna_terminus_xml.py",
        "--jobs-dir",
        "evals/tb2_laguna_terminus_xml/full",
        "--job-name",
        "laguna-xs2-openrouter-key2-native-toolcall-timeoutx20-detached-full",
        "--n-concurrent",
        "1",
        "--max-turns",
        "64",
        "--max-retries",
        "0",
        "--request-timeout",
        "120",
        "--min-request-interval",
        "15.0",
        "--timeout-multiplier",
        "20",
        "--skip-probe",
    ]
    return subprocess.run(command, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
