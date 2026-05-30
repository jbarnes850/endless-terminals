# test_final_state.py
from pathlib import Path
import re

BASE = Path("/home/user/cluster_observability")
OUTPUT_FILE = Path("/home/user/cluster_observability/alert_decision.log")

EXPECTED_SOURCE_FILES = {
    Path("/home/user/cluster_observability/topology.txt"): """cluster: orders-prod-sim
replication_model: leader_follower
leader: node-b
followers: node-a,node-c
client_write_path: api-gateway -> leader -> followers
alert_policy: alert only on the node whose symptoms explain replicated write instability
""",
    Path("/home/user/cluster_observability/node-a/health.txt"): """node=node-a
role=follower
process=running
disk=ok
network=ok
last_restart_minutes_ago=1440
local_health=green
note=historical latency spike cleared before current incident window
""",
    Path("/home/user/cluster_observability/node-b/health.txt"): """node=node-b
role=leader
process=running
disk=ok
network=degraded
last_restart_minutes_ago=1440
local_health=yellow
note=leader accepts writes but follower replication acknowledgements are timing out
""",
    Path("/home/user/cluster_observability/node-c/health.txt"): """node=node-c
role=follower
process=running
disk=ok
network=ok
last_restart_minutes_ago=12
local_health=yellow
note=recent restart completed successfully and replica is caught up
""",
    Path("/home/user/cluster_observability/node-a/metrics.prom"): """# HELP orders_rpc_p95_ms RPC p95 latency in milliseconds
# TYPE orders_rpc_p95_ms gauge
orders_rpc_p95_ms{node="node-a"} 41
# HELP orders_replication_lag_seconds replica lag in seconds
# TYPE orders_replication_lag_seconds gauge
orders_replication_lag_seconds{node="node-a"} 0
# HELP orders_write_error_rate_percent write error rate percent
# TYPE orders_write_error_rate_percent gauge
orders_write_error_rate_percent{node="node-a"} 0.1
# HELP orders_network_retransmits_total network retransmits total
# TYPE orders_network_retransmits_total counter
orders_network_retransmits_total{node="node-a"} 12
""",
    Path("/home/user/cluster_observability/node-b/metrics.prom"): """# HELP orders_rpc_p95_ms RPC p95 latency in milliseconds
# TYPE orders_rpc_p95_ms gauge
orders_rpc_p95_ms{node="node-b"} 920
# HELP orders_replication_lag_seconds replica lag in seconds
# TYPE orders_replication_lag_seconds gauge
orders_replication_lag_seconds{node="node-b"} 0
# HELP orders_write_error_rate_percent write error rate percent
# TYPE orders_write_error_rate_percent gauge
orders_write_error_rate_percent{node="node-b"} 18.7
# HELP orders_network_retransmits_total network retransmits total
# TYPE orders_network_retransmits_total counter
orders_network_retransmits_total{node="node-b"} 8841
""",
    Path("/home/user/cluster_observability/node-c/metrics.prom"): """# HELP orders_rpc_p95_ms RPC p95 latency in milliseconds
# TYPE orders_rpc_p95_ms gauge
orders_rpc_p95_ms{node="node-c"} 58
# HELP orders_replication_lag_seconds replica lag in seconds
# TYPE orders_replication_lag_seconds gauge
orders_replication_lag_seconds{node="node-c"} 2
# HELP orders_write_error_rate_percent write error rate percent
# TYPE orders_write_error_rate_percent gauge
orders_write_error_rate_percent{node="node-c"} 0.3
# HELP orders_network_retransmits_total network retransmits total
# TYPE orders_network_retransmits_total counter
orders_network_retransmits_total{node="node-c"} 34
""",
    Path("/home/user/cluster_observability/recent-events.log"): """2026-05-29T09:14:01Z node-a info follower heartbeat ok
2026-05-29T09:14:03Z node-c warn restarted worker after maintenance window
2026-05-29T09:14:18Z node-b warn retransmit burst on leader replication socket
2026-05-29T09:14:21Z node-b error follower ack timeout while committing order batch
2026-05-29T09:14:24Z node-a info replica applied batch 88402
2026-05-29T09:14:26Z node-c info replica caught up after restart
2026-05-29T09:14:29Z node-b error client write failed after quorum timeout
2026-05-29T09:14:33Z node-b warn retransmit burst on leader replication socket
""",
}

LOWERCASE_HYPHEN_VALUE = r"[a-z0-9]+(?:-[a-z0-9]+)*"


def _read_output_lines():
    assert OUTPUT_FILE.exists(), (
        f"Required final output file is missing: {OUTPUT_FILE}. "
        "Create exactly this file with the six required decision lines."
    )
    assert OUTPUT_FILE.is_file(), (
        f"Required final output path is not a regular file: {OUTPUT_FILE}"
    )

    content = OUTPUT_FILE.read_text(encoding="utf-8")
    assert content, f"{OUTPUT_FILE} is empty; it must contain exactly six non-empty lines."

    raw_lines = content.splitlines()
    assert content.endswith("\n"), (
        f"{OUTPUT_FILE} should end after line 6 with a newline, not with unterminated text."
    )
    assert len(raw_lines) == 6, (
        f"{OUTPUT_FILE} must contain exactly 6 lines; found {len(raw_lines)} lines: "
        f"{raw_lines!r}"
    )

    blank_line_numbers = [idx for idx, line in enumerate(raw_lines, start=1) if line == ""]
    assert not blank_line_numbers, (
        f"{OUTPUT_FILE} must contain no blank lines; blank line(s) found at: "
        f"{blank_line_numbers}"
    )

    whitespace_line_numbers = [
        idx for idx, line in enumerate(raw_lines, start=1)
        if line != line.strip()
    ]
    assert not whitespace_line_numbers, (
        f"{OUTPUT_FILE} lines must not have leading/trailing whitespace; "
        f"problem line(s): {whitespace_line_numbers}"
    )

    return raw_lines


def test_source_evidence_files_remain_unchanged():
    for file_path, expected_content in EXPECTED_SOURCE_FILES.items():
        assert file_path.exists(), f"Source evidence file was removed or is missing: {file_path}"
        assert file_path.is_file(), f"Source evidence path is no longer a file: {file_path}"
        actual_content = file_path.read_text(encoding="utf-8")
        assert actual_content == expected_content, (
            f"Source evidence file was modified but must remain unchanged: {file_path}"
        )


def test_alert_decision_log_has_exactly_six_non_empty_lines_with_no_extra_content():
    _read_output_lines()


def test_checkpoint_lines_are_in_required_order_and_format():
    lines = _read_output_lines()

    expected_prefixes = [
        "CHECKPOINT topology=",
        "CHECKPOINT health=",
        "CHECKPOINT metrics=",
        "CHECKPOINT events=",
    ]

    for line_number, (line, prefix) in enumerate(zip(lines[:4], expected_prefixes), start=1):
        assert line.startswith(prefix), (
            f"Line {line_number} must begin with exactly {prefix!r}; got {line!r}"
        )
        value = line[len(prefix):]
        assert re.fullmatch(LOWERCASE_HYPHEN_VALUE, value), (
            f"Line {line_number} finding must be lowercase words/numbers joined by hyphens "
            f"with no spaces; got {value!r}"
        )


def test_checkpoint_values_semantically_reflect_required_evidence_convergence():
    lines = _read_output_lines()

    topology_value = lines[0].split("=", 1)[1]
    assert "node-b" in topology_value, (
        "Line 1 topology checkpoint must account for topology by identifying node-b "
        f"as the leader / write path node; got {topology_value!r}"
    )
    assert any(token in topology_value for token in ("leader", "writes", "write", "through")), (
        "Line 1 topology checkpoint should mention node-b's leadership or write-path role; "
        f"got {topology_value!r}"
    )

    health_value = lines[1].split("=", 1)[1]
    assert (
        "node-b" in health_value
        or "node-c" in health_value
        or "yellow" in health_value
        or "network" in health_value
    ), (
        "Line 2 health checkpoint must show health evidence was considered, such as "
        "node-b network degradation or distinguishing node-c's non-causal restart; "
        f"got {health_value!r}"
    )
    assert any(
        token in health_value
        for token in ("network", "degraded", "restart", "noncausal", "caught", "yellow", "separated")
    ), (
        "Line 2 health checkpoint does not clearly reflect the relevant health finding "
        "or false-lead separation; got "
        f"{health_value!r}"
    )

    metrics_value = lines[2].split("=", 1)[1]
    assert "node-b" in metrics_value, (
        "Line 3 metrics checkpoint must identify node-b as the node with bad current "
        f"metrics; got {metrics_value!r}"
    )
    assert any(
        token in metrics_value
        for token in ("metrics", "bad", "retransmits", "errors", "latency", "high", "write")
    ), (
        "Line 3 metrics checkpoint should describe node-b's bad metrics "
        "(high latency/errors/retransmits); got "
        f"{metrics_value!r}"
    )

    events_value = lines[3].split("=", 1)[1]
    assert "node-b" in events_value, (
        "Line 4 events checkpoint must identify node-b as matching the current event "
        f"evidence; got {events_value!r}"
    )
    assert any(
        token in events_value
        for token in ("events", "match", "ack", "timeouts", "timeout", "write", "failures", "retransmit")
    ), (
        "Line 4 events checkpoint should describe node-b's retransmits, ack timeouts, "
        f"or write failures; got {events_value!r}"
    )


def test_alert_line_targets_node_b_with_valid_causal_reason():
    lines = _read_output_lines()
    alert_line = lines[4]

    match = re.fullmatch(rf"ALERT node=(node-[abc]) reason=({LOWERCASE_HYPHEN_VALUE})", alert_line)
    assert match, (
        "Line 5 must be exactly formatted as "
        "'ALERT node=<node-a|node-b|node-c> reason=<lowercase-hyphenated-reason>'; "
        f"got {alert_line!r}"
    )

    node_name, reason = match.groups()
    assert node_name == "node-b", (
        f"Line 5 alerts on {node_name}, but the combined topology, health, metrics, "
        "and events converge on node-b. Do not alert on node-a's historical note or "
        "node-c's harmless restart."
    )
    assert any(
        token in reason
        for token in (
            "leader",
            "replication",
            "replicated",
            "timeouts",
            "timeout",
            "network",
            "retransmits",
            "write",
            "writes",
            "failing",
            "failures",
            "instability",
        )
    ), (
        "Line 5 reason should describe the causal leader network/replication/write "
        f"instability; got reason={reason!r}"
    )


def test_stop_line_confirms_verification():
    lines = _read_output_lines()
    assert lines[5] == "STOP verified=yes", (
        "Line 6 must be exactly 'STOP verified=yes' after the file has been "
        f"format-verified; got {lines[5]!r}"
    )