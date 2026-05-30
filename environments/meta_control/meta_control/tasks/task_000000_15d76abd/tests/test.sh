#!/bin/bash
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
printf '\n__ET_CHECKPOINTS__\n'
cat /logs/verifier/checkpoints.json 2>/dev/null || true
printf '\n__ET_CHECKPOINTS_END__\n'
if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
