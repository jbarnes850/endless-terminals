#!/bin/bash
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
