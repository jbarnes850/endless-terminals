from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from meta_control.environment import (
    LAGUNA_XML_RUNNER_SOURCE,
    LAGUNA_XML_STATE_INPUT_PATH,
    LAGUNA_XML_STATE_OUTPUT_PATH,
    LAGUNA_XML_TOOL_DEFS_PATH,
    META_CONTROL_TASK_SETUP_PATH,
    MetaControlHarness,
    MetaControlHarnessConfig,
    action_fingerprints,
    action_observation_fingerprints,
    ensure_top_level_sampling_args,
    extract_endless_docker_post,
    parse_laguna_xml_tool_calls,
    task_environment_setup_script,
    with_task_environment_setup,
)


def test_parse_laguna_xml_tool_call_and_metrics_see_observation() -> None:
    content = """<tool_call>shell
<arg_key>command</arg_key>
<arg_value>echo hi</arg_value>
</tool_call>"""

    calls = parse_laguna_xml_tool_calls(content)

    assert calls == [
        {
            "id": "laguna_xml_call_0",
            "type": "function",
            "function": {
                "name": "shell",
                "arguments": json.dumps({"command": "echo hi"}, sort_keys=True),
            },
        }
    ]
    state = {
        "trajectory": [
            {
                "completion": [
                    {"role": "assistant", "content": content},
                    {"role": "tool", "tool_call_id": "laguna_xml_call_0", "content": "exit_code=0\nstdout:\nhi\n"},
                ]
            }
        ]
    }
    assert action_fingerprints(state) == ['shell:{"command":"echo hi"}']
    assert action_observation_fingerprints(state) == ['shell:{"command":"echo hi"}->exit_code=0\nstdout:\nhi']

    structured_state = {
        "trajectory": [
            {
                "completion": [
                    {"role": "assistant", "tool_calls": calls},
                    {"role": "tool", "tool_call_id": "laguna_xml_call_0", "content": "exit_code=0\nstdout:\nhi\n"},
                ]
            }
        ]
    }
    assert action_fingerprints(structured_state) == ['shell:{"command":"echo hi"}']


def test_runner_executes_laguna_xml_shell_call_and_records_trajectory(tmp_path: Path) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    runner = tmp_path / "runner.py"
    runner.write_text(LAGUNA_XML_RUNNER_SOURCE, encoding="utf-8")
    xml_content = """<tool_call>
bash
<arg_key>command</arg_key>
<arg_value>echo ok > /tmp/xml_contract_passed; python3 -c 'print("x" * 10000)'</arg_value>
</tool_call>"""
    fake_openai = tmp_path / "openai.py"
    fake_openai.write_text(
        """
class _Message:
    def model_dump(self, mode=None, exclude_none=True):
        return {
            "role": "assistant",
            "content": XML_CONTENT,
        }


class _Choice:
    message = _Message()


class _Response:
    choices = [_Choice()]


class _Completions:
    async def create(self, **kwargs):
        return _Response()


class _Chat:
    completions = _Completions()


class AsyncOpenAI:
    def __init__(self, **kwargs):
        self.chat = _Chat()

    async def close(self):
        return None
""".replace("XML_CONTENT", repr(xml_content)),
        encoding="utf-8",
    )

    class StopHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"done": false}')

        def log_message(self, format: str, *args: object) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), StopHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    try:
        Path("/tmp/xml_contract_passed").unlink(missing_ok=True)
        Path(LAGUNA_XML_STATE_INPUT_PATH).write_text(
            json.dumps(
                {
                    "prompt": [{"role": "user", "content": "write result"}],
                    "runtime": {
                        "model": "laguna",
                        "sampling_args": {"max_tokens": 64, "temperature": 0},
                    },
                    "endpoint_root_url": endpoint,
                    "endpoint_base_url": endpoint + "/v1",
                    "trajectory_id": "contract",
                }
            ),
            encoding="utf-8",
        )
        Path(LAGUNA_XML_TOOL_DEFS_PATH).write_text(
            json.dumps({"tools": [], "remote_tool_names": [], "max_turns": 1}),
            encoding="utf-8",
        )
        Path(LAGUNA_XML_STATE_OUTPUT_PATH).unlink(missing_ok=True)
        env = {
            **os.environ,
            "PYTHONPATH": str(tmp_path),
            "AGENT_WORKDIR": str(workdir),
            "META_CONTROL_TOOL_OBSERVATION_CHAR_LIMIT": "600",
        }

        completed = subprocess.run(
            [sys.executable, str(runner)],
            check=True,
            text=True,
            capture_output=True,
            env=env,
        )

        assert completed.stderr == ""
        assert Path("/tmp/xml_contract_passed").read_text(encoding="utf-8") == "ok\n"
        patch = json.loads(Path(LAGUNA_XML_STATE_OUTPUT_PATH).read_text(encoding="utf-8"))
        assert patch["sampling_args"] == {"max_tokens": 64, "temperature": 0}
        assert patch["stop_condition"] == "max_turns_reached"
        trajectory = patch["trajectory"]
        assistant_message = trajectory[0]["completion"][0]
        tool_message = trajectory[0]["completion"][1]
        assert assistant_message["role"] == "assistant"
        assert assistant_message["content"] == xml_content
        assert assistant_message["tool_calls"] == parse_laguna_xml_tool_calls(xml_content)
        assert tool_message["role"] == "tool"
        assert tool_message["tool_call_id"] == "laguna_xml_call_0"
        assert "exit_code=0" in tool_message["content"]
        assert "[meta_control: tool output truncated" in tool_message["content"]
        assert len(tool_message["content"]) <= 600

        state = {"trajectory": trajectory}
        expected_action = 'bash:{"command":"echo ok > /tmp/xml_contract_passed; python3 -c \'print(\\"x\\" * 10000)\'"}'
        assert action_fingerprints(state) == [expected_action]
        observation_fingerprints = action_observation_fingerprints(state)
        assert len(observation_fingerprints) == 1
        assert observation_fingerprints[0].startswith(expected_action + "->exit_code=0")
        assert "[meta_control: tool output truncated" in observation_fingerprints[0]
        rollout_metrics = patch["meta_control_rollout_metrics"]
        assert rollout_metrics["raw_observation_tokens"] > rollout_metrics["compacted_observation_tokens"]
        assert rollout_metrics["truncated_bytes"] > 0
        assert rollout_metrics["compaction_events"] == 1

        harness = MetaControlHarness(config=MetaControlHarnessConfig())
        incomplete_state = {"trajectory": trajectory, "metrics": {"harbor_reward": 0.0}}
        complete_state = {"trajectory": trajectory, "metrics": {"harbor_reward": 1.0}}
        assert asyncio.run(harness.gated_progress(incomplete_state)) == 0.0
        assert asyncio.run(harness.gated_progress(complete_state)) == harness.config.gated_progress_weight
    finally:
        Path("/tmp/xml_contract_passed").unlink(missing_ok=True)
        server.shutdown()
        server.server_close()


def test_parent_harness_promotes_runtime_sampling_args_for_prime_rl_state_column() -> None:
    state = {
        "sampling_args": None,
        "runtime": {
            "sampling_args": {
                "temperature": 1.0,
                "max_completion_tokens": 4096,
                "extra_body": {"return_token_ids": True, "cache_salt": "abc"},
            }
        },
    }

    ensure_top_level_sampling_args(state)

    assert state["sampling_args"] == {
        "temperature": 1.0,
        "max_completion_tokens": 4096,
        "extra_body": {"return_token_ids": True, "cache_salt": "abc"},
    }


def test_harbor_dockerfile_setup_is_injected_before_laguna_runner() -> None:
    task_dir = Path(__file__).parents[1] / "meta_control" / "tasks" / "task_000000_f3c8f023"
    dockerfile = task_dir / "environment" / "Dockerfile"
    body = extract_endless_docker_post(dockerfile.read_text(encoding="utf-8"))

    assert body is not None
    assert "mkdir -p /home/user/sre-uptime-check" in body
    assert "catalog_api_server.py" in body

    task = {
        "task_dir": str(task_dir),
        "harbor": {"config": {"environment": {"build_timeout_sec": 123}}},
    }
    setup_script = task_environment_setup_script(task)
    assert setup_script is not None
    assert "mkdir -p /home/user/sre-uptime-check" in setup_script
    assert "/usr/local/bin/start_*" in setup_script

    program = {
        "base": True,
        "sandbox": True,
        "files": {"/tmp/existing": "ok"},
        "env": {"AGENT_WORKDIR": "/app", "KEEP": "1"},
    }
    patched = with_task_environment_setup(program, task)

    assert patched["files"]["/tmp/existing"] == "ok"
    assert patched["files"][META_CONTROL_TASK_SETUP_PATH] == setup_script
    assert patched["env"]["AGENT_WORKDIR"] == "/home/user"
    assert patched["env"]["KEEP"] == "1"
    assert patched["setup"] == [f"bash {META_CONTROL_TASK_SETUP_PATH}"]
    assert patched["setup_timeout"] == 123
