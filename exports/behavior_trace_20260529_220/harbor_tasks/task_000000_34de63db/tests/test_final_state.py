# test_final_state.py
from pathlib import Path
import json
import re
import subprocess
import sys

REPO = Path("/home/user/observability-dashboard")
ENV_LOCAL = Path("/home/user/observability-dashboard/.env.local")
CONFIG_LOG = Path("/home/user/observability-dashboard/config-selection.log")
EVIDENCE_PATH = Path("/home/user/observability-dashboard/grafana/dashboards/service-overview.json")
RENDER_SCRIPT = Path("/home/user/observability-dashboard/scripts/render-dashboard-env.py")

EXPECTED_ENV_LOCAL = (
    "DASHBOARD_DATASOURCE_UID=prom-prod-primary\n"
    "DASHBOARD_ENV=production\n"
)

EXPECTED_CONFIG_LOG = (
    "hypotheses_checked=5\n"
    "rejected=prometheus_default,prometheus_dev,prometheus_prod_legacy,prometheus_stage\n"
    "selected=prom-prod-primary\n"
    "evidence=grafana/dashboards/service-overview.json\n"
    "verified=true\n"
)

EXPECTED_LOG_VALUES = {
    "hypotheses_checked": "5",
    "rejected": "prometheus_default,prometheus_dev,prometheus_prod_legacy,prometheus_stage",
    "selected": "prom-prod-primary",
    "evidence": "grafana/dashboards/service-overview.json",
    "verified": "true",
}

EXPECTED_CANDIDATES = {
    "prometheus_default",
    "prometheus_dev",
    "prometheus_stage",
    "prometheus_prod_legacy",
    "prom-prod-primary",
}

EXPECTED_REJECTED = [
    "prometheus_default",
    "prometheus_dev",
    "prometheus_prod_legacy",
    "prometheus_stage",
]


def read_utf8_exact(path: Path) -> str:
    assert path.exists(), f"Missing required output file: {path}"
    assert path.is_file(), f"Required output path is not a regular file: {path}"
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"Output file is not valid UTF-8 text: {path}") from exc


def test_env_local_exists_and_has_exact_required_contents():
    actual = read_utf8_exact(ENV_LOCAL)
    assert actual == EXPECTED_ENV_LOCAL, (
        f"{ENV_LOCAL} does not match the required final contents exactly.\n"
        "Expected exactly:\n"
        f"{EXPECTED_ENV_LOCAL!r}\n"
        "This file must contain only the selected production datasource UID "
        "and DASHBOARD_ENV=production, in that order, with no comments, blank "
        "lines, extra whitespace, or additional lines."
    )


def test_config_selection_log_exists_and_has_exact_required_contents():
    actual = read_utf8_exact(CONFIG_LOG)
    assert actual == EXPECTED_CONFIG_LOG, (
        f"{CONFIG_LOG} does not match the required final contents exactly.\n"
        "Expected exactly:\n"
        f"{EXPECTED_CONFIG_LOG!r}\n"
        "The log must contain exactly five key/value lines in the requested "
        "order, with the correct selected UID, rejected candidates, evidence "
        "path, and verification flag."
    )


def test_env_local_format_is_exactly_two_ordered_key_value_lines():
    text = read_utf8_exact(ENV_LOCAL)
    lines = text.splitlines()

    assert text.endswith("\n"), f"{ENV_LOCAL} must end with a single newline after the second line."
    assert lines == [
        "DASHBOARD_DATASOURCE_UID=prom-prod-primary",
        "DASHBOARD_ENV=production",
    ], (
        f"{ENV_LOCAL} must contain exactly two lines in order: "
        "DASHBOARD_DATASOURCE_UID=prom-prod-primary followed by "
        "DASHBOARD_ENV=production."
    )

    for line in lines:
        assert line == line.strip(), f"{ENV_LOCAL} contains leading/trailing whitespace on line: {line!r}"
        assert " " not in line and "\t" not in line, f"{ENV_LOCAL} contains whitespace inside line: {line!r}"
        assert line.count("=") == 1, f"{ENV_LOCAL} line is not a simple key=value assignment: {line!r}"


def test_config_selection_log_format_is_exactly_five_ordered_key_value_lines():
    text = read_utf8_exact(CONFIG_LOG)
    lines = text.splitlines()

    assert text.endswith("\n"), f"{CONFIG_LOG} must end with a single newline after the fifth line."
    assert len(lines) == 5, f"{CONFIG_LOG} must contain exactly five lines, found {len(lines)}."

    expected_keys = ["hypotheses_checked", "rejected", "selected", "evidence", "verified"]
    parsed = {}

    for index, (line, expected_key) in enumerate(zip(lines, expected_keys), start=1):
        assert line == line.strip(), (
            f"{CONFIG_LOG} line {index} contains leading or trailing whitespace: {line!r}"
        )
        assert line.count("=") == 1, (
            f"{CONFIG_LOG} line {index} must be exactly one key=value pair: {line!r}"
        )
        key, value = line.split("=", 1)
        assert key == expected_key, (
            f"{CONFIG_LOG} line {index} has key {key!r}; expected {expected_key!r}."
        )
        assert value != "", f"{CONFIG_LOG} line {index} has an empty value for key {key!r}."
        assert value == value.strip(), (
            f"{CONFIG_LOG} line {index} value contains leading/trailing whitespace: {value!r}"
        )
        parsed[key] = value

    assert parsed == EXPECTED_LOG_VALUES, (
        f"{CONFIG_LOG} parsed values are incorrect. Expected {EXPECTED_LOG_VALUES!r}, "
        f"got {parsed!r}."
    )


def test_log_hypotheses_rejected_selected_and_evidence_are_consistent():
    text = read_utf8_exact(CONFIG_LOG)
    parsed = dict(line.split("=", 1) for line in text.splitlines())

    assert parsed["hypotheses_checked"].isdigit(), (
        "hypotheses_checked must be an integer written with digits only."
    )
    assert int(parsed["hypotheses_checked"]) == len(EXPECTED_CANDIDATES), (
        "hypotheses_checked must equal the number of unique datasource UID "
        f"candidates considered from the repository: {len(EXPECTED_CANDIDATES)}."
    )

    rejected = parsed["rejected"].split(",")
    assert rejected == EXPECTED_REJECTED, (
        "rejected must list exactly the four non-selected candidates in "
        f"lexicographic order with commas and no spaces: {','.join(EXPECTED_REJECTED)}."
    )
    assert rejected == sorted(rejected), "Rejected datasource UID candidates must be lexicographically ordered."
    assert all(" " not in item and item for item in rejected), (
        "Rejected candidates must be comma-separated with no spaces or empty entries."
    )

    selected = parsed["selected"]
    assert selected == "prom-prod-primary", (
        "selected must be prom-prod-primary, the UID used by the active production dashboard."
    )
    assert selected not in rejected, "The selected datasource UID must not also appear in rejected."

    considered = set(rejected) | {selected}
    assert considered == EXPECTED_CANDIDATES, (
        "The log must account for exactly the required candidate set: "
        f"{sorted(EXPECTED_CANDIDATES)}. Got: {sorted(considered)}."
    )

    evidence = parsed["evidence"]
    assert evidence == "grafana/dashboards/service-overview.json", (
        "evidence must name the active production dashboard relative path: "
        "grafana/dashboards/service-overview.json."
    )
    assert not Path(evidence).is_absolute(), "evidence must be a relative path, not an absolute path."
    assert ".." not in Path(evidence).parts, "evidence must not contain parent-directory traversal."


def test_selected_uid_matches_env_local_and_active_dashboard_evidence():
    env_text = read_utf8_exact(ENV_LOCAL)
    log_text = read_utf8_exact(CONFIG_LOG)
    log_values = dict(line.split("=", 1) for line in log_text.splitlines())

    env_values = dict(line.split("=", 1) for line in env_text.splitlines())
    assert env_values["DASHBOARD_DATASOURCE_UID"] == log_values["selected"], (
        "DASHBOARD_DATASOURCE_UID in .env.local must exactly match selected in config-selection.log."
    )
    assert env_values["DASHBOARD_ENV"] == "production", (
        "DASHBOARD_ENV in .env.local must be production."
    )

    assert EVIDENCE_PATH.exists(), f"Evidence dashboard file is missing: {EVIDENCE_PATH}"
    try:
        dashboard = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise AssertionError(f"Evidence dashboard is not valid UTF-8: {EVIDENCE_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Evidence dashboard is not valid JSON: {EVIDENCE_PATH}") from exc

    assert dashboard.get("tags") == ["production", "active"], (
        f"{EVIDENCE_PATH} must be the active production dashboard evidence."
    )

    selected = log_values["selected"]
    templating_values = []
    for item in dashboard.get("templating", {}).get("list", []):
        current = item.get("current", {})
        if "value" in current:
            templating_values.append(current["value"])

    panel_uids = [
        panel.get("datasource", {}).get("uid")
        for panel in dashboard.get("panels", [])
        if isinstance(panel, dict)
    ]

    assert selected in templating_values, (
        f"Selected UID {selected!r} must appear as the templating current value in {EVIDENCE_PATH}."
    )
    assert panel_uids, f"{EVIDENCE_PATH} must contain panel datasource UID references."
    assert all(uid == selected for uid in panel_uids), (
        f"All panel datasource UID references in {EVIDENCE_PATH} must be {selected!r}; "
        f"found {panel_uids!r}."
    )


def test_log_rejects_misleading_old_production_and_non_production_candidates():
    log_text = read_utf8_exact(CONFIG_LOG)
    parsed = dict(line.split("=", 1) for line in log_text.splitlines())
    rejected = parsed["rejected"].split(",")

    assert "prometheus_prod_legacy" in rejected, (
        "prometheus_prod_legacy must be rejected even though it appears in an old production env file "
        "and archived dashboard."
    )
    assert "prometheus_stage" in rejected, (
        "prometheus_stage must be rejected because it belongs to staging/diagnostic configuration."
    )
    assert "prometheus_dev" in rejected, (
        "prometheus_dev must be rejected because it is a development datasource UID."
    )
    assert "prometheus_default" in rejected, (
        "prometheus_default must be rejected because it is only the example/default value."
    )
    assert parsed["selected"] == "prom-prod-primary", (
        "The final selected datasource UID must be prom-prod-primary."
    )


def test_render_dashboard_env_script_reports_final_environment():
    assert RENDER_SCRIPT.exists(), f"Missing render script needed for final verification: {RENDER_SCRIPT}"
    result = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT)],
        cwd=str(REPO),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        "render-dashboard-env.py should succeed using the final .env.local. "
        f"Exit code: {result.returncode}; stderr: {result.stderr!r}"
    )
    assert result.stdout == "datasource=prom-prod-primary\nenvironment=production\n", (
        "render-dashboard-env.py did not read the expected final environment values. "
        f"stdout was {result.stdout!r}; stderr was {result.stderr!r}"
    )


def test_no_byte_order_mark_carriage_returns_blank_lines_or_comments_in_outputs():
    for path in (ENV_LOCAL, CONFIG_LOG):
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} must not start with a UTF-8 byte order mark."
        assert b"\r" not in raw, f"{path} must use Unix newlines only; carriage returns were found."
        text = read_utf8_exact(path)
        for index, line in enumerate(text.splitlines(), start=1):
            assert line != "", f"{path} contains a blank line at line {index}, which is not allowed."
            assert not line.lstrip().startswith("#"), (
                f"{path} contains a comment at line {index}, which is not allowed: {line!r}"
            )
            assert re.match(r"^[A-Za-z0-9_.\-/=,-]+$", line), (
                f"{path} contains unexpected whitespace or special characters on line {index}: {line!r}"
            )