FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eu

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    mkdir -p /home/user/solver_case

    cat > /home/user/solver_case/events.csv <<'EOF'
event_id,service,severity,region,pattern_id
1,auth,high,us-east,P03
2,billing,medium,us-east,P01
3,auth,medium,eu-west,P03
4,checkout,high,us-east,P02
5,billing,high,eu-west,P04
6,checkout,medium,us-east,P02
7,auth,low,us-east,P03
8,billing,medium,ap-south,P01
9,checkout,high,eu-west,P02
10,search,medium,us-east,P05
11,search,high,eu-west,P05
12,billing,low,us-east,P04
EOF

    cat > /home/user/solver_case/select_patterns.py <<'PY'
#!/usr/bin/env python3
import csv
import itertools
import json
from pathlib import Path

EVENTS_CSV = Path("/home/user/solver_case/events.csv")
OUTPUT_DIR = Path("/home/user/solver_case/output")
CANDIDATE_SUMMARY = OUTPUT_DIR / "candidate_summary.txt"
FINAL_SOLUTION = OUTPUT_DIR / "final_solution.json"

PATTERNS = {
    "P01": {"events": [2, 8], "score": 9},
    "P02": {"events": [4, 6, 9], "score": 15},
    "P03": {"events": [1, 3, 7], "score": 14},
    "P04": {"events": [5, 12], "score": 8},
    "P05": {"events": [10, 11], "score": 10},
}

CHOOSE_EXACTLY = 3


def read_events():
    with EVENTS_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_candidate_artifact():
    CANDIDATE_SUMMARY.write_text(
        "candidate_status=generated\n"
        "candidate_patterns=P01,P03\n"
        "candidate_score=17\n"
        "note=not final optimization solution\n",
        encoding="utf-8",
    )


def solve():
    best_patterns = None
    best_score = None
    best_covered = None

    pattern_ids = sorted(PATTERNS)
    for combo in itertools.combinations(pattern_ids, CHOOSE_EXACTLY):
        score = sum(PATTERNS[pid]["score"] for pid in combo)
        covered_events = sorted(
            set().union(*(PATTERNS[pid]["events"] for pid in combo))
        )
        if (
            best_score is None
            or score > best_score
            or (score == best_score and list(combo) < best_patterns)
        ):
            best_patterns = list(combo)
            best_score = score
            best_covered = covered_events

    return {
        "solver_status": "OPTIMAL",
        "selected_patterns": best_patterns,
        "selected_count": len(best_patterns),
        "covered_events": len(best_covered),
        "total_score": best_score,
    }


def main():
    read_events()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_candidate_artifact()
    solution = solve()
    FINAL_SOLUTION.write_text(
        json.dumps(solution, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
PY

    cat > /home/user/solver_case/check_report.py <<'PY'
#!/usr/bin/env python3
import re
import sys
from pathlib import Path

REPORT_PATH = Path("/home/user/solver_case/pattern_report.txt")
SUCCESS = "REPORT CHECK PASSED: optimal pattern report verified"

EXPECTED_LINES = [
    "solver_status=OPTIMAL",
    "selected_count=3",
    "selected_patterns=P02,P03,P05",
    "covered_events=8",
    "total_score=39",
]


def fail(message: str) -> int:
    print(f"REPORT CHECK FAILED: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not REPORT_PATH.exists():
        return fail(f"missing report file: {REPORT_PATH}")
    if not REPORT_PATH.is_file():
        return fail(f"report path is not a regular file: {REPORT_PATH}")

    raw = REPORT_PATH.read_text(encoding="utf-8")

    if raw.endswith("\n"):
        body = raw[:-1]
        if body.endswith("\n"):
            return fail("report has extra trailing blank line or too many lines")
    else:
        body = raw

    lines = body.split("\n")
    if len(lines) != 5:
        return fail(f"expected exactly 5 non-empty lines, found {len(lines)}")

    for idx, line in enumerate(lines, start=1):
        if line == "":
            return fail(f"line {idx} is blank")
        if line != line.rstrip(" "):
            return fail(f"line {idx} has trailing spaces")
        if line != line.rstrip("\t"):
            return fail(f"line {idx} has trailing tabs")

    if lines != EXPECTED_LINES:
        for idx, (actual, expected) in enumerate(zip(lines, EXPECTED_LINES), start=1):
            if actual != expected:
                return fail(
                    f"line {idx} mismatch: expected {expected!r}, got {actual!r}"
                )
        return fail("report contents do not match expected values")

    selected = lines[2].split("=", 1)[1]
    parts = selected.split(",")
    if parts != sorted(parts):
        return fail("selected patterns are not in ascending order")
    if not all(re.fullmatch(r"P\d{2}", part) for part in parts):
        return fail("selected patterns are not comma-separated pattern IDs")

    print(SUCCESS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

    chmod 755 /home/user/solver_case/select_patterns.py
    chmod 755 /home/user/solver_case/check_report.py
    chmod 666 /home/user/solver_case/events.csv
    chmod 777 /home/user /home/user/solver_case

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
