# test_final_state.py
from pathlib import Path
import os


BASE = Path("/home/user/cert-rollout")
LEGACY_PEM = Path("/home/user/cert-rollout/legacy/live-api.pem")
CURRENT_CERT_ENV = Path("/home/user/cert-rollout/deploy/current-cert.env")
VERIFICATION_LOG = Path("/home/user/cert-rollout/deploy/rollout-verification.log")

EXPECTED_ENV_LINES = [
    "CERT_COMMON_NAME=api.staging.internal",
    "CERT_SERIAL=7B:91:03:DE:44:18",
    "CERT_NOT_AFTER=2026-08-17T23:59:59Z",
    "CERT_SOURCE=deploy/current-cert.env",
]

EXPECTED_LOG_LINES = [
    "rollout=certificate-metadata-migration",
    "new_source=/home/user/cert-rollout/deploy/current-cert.env",
    "legacy_source_retired=yes",
    "verified_common_name=api.staging.internal",
    "verified_serial=7B:91:03:DE:44:18",
    "verified_not_after=2026-08-17T23:59:59Z",
]

EXPECTED_ENV_VALUES = {
    "CERT_COMMON_NAME": "api.staging.internal",
    "CERT_SERIAL": "7B:91:03:DE:44:18",
    "CERT_NOT_AFTER": "2026-08-17T23:59:59Z",
    "CERT_SOURCE": "deploy/current-cert.env",
}


def _read_lines_tolerating_one_trailing_newline(path: Path) -> list[str]:
    """
    Return logical file lines while tolerating normal final newline behavior.

    This rejects extra blank lines because splitlines() preserves interior and
    repeated trailing blank logical lines, e.g. 'a\\n\\n'.splitlines() == ['a', ''].
    """
    return path.read_text(encoding="utf-8").splitlines()


def _assert_regular_readable_file(path: Path, description: str) -> None:
    assert path.exists(), f"{description} is missing: {path}"
    assert path.is_file(), f"{description} must be a regular file: {path}"
    assert os.access(path, os.R_OK), f"{description} is not readable by the task user: {path}"


def _parse_env_lines(lines: list[str]) -> dict[str, str]:
    parsed = {}
    for index, line in enumerate(lines, start=1):
        assert "=" in line, f"Env line {index} is missing '=': {line!r}"
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def test_new_deployment_env_exists_as_exact_source_of_truth():
    """The new deployment manifest must exist and contain exactly the migrated metadata."""
    _assert_regular_readable_file(CURRENT_CERT_ENV, "New certificate env source")

    actual_lines = _read_lines_tolerating_one_trailing_newline(CURRENT_CERT_ENV)
    assert actual_lines == EXPECTED_ENV_LINES, (
        f"{CURRENT_CERT_ENV} does not contain the exact required four env lines in order.\n"
        "It must contain no quotes, extra spaces around '=', blank lines, comments, "
        "legacy PEM data, missing keys, extra keys, or reordered keys.\n"
        f"Expected lines:\n{EXPECTED_ENV_LINES!r}\n"
        f"Actual lines:\n{actual_lines!r}"
    )


def test_new_env_preserves_active_certificate_metadata_exactly():
    """Migrated values must preserve common name, serial formatting, and expiration exactly."""
    _assert_regular_readable_file(CURRENT_CERT_ENV, "New certificate env source")
    actual_lines = _read_lines_tolerating_one_trailing_newline(CURRENT_CERT_ENV)
    parsed = _parse_env_lines(actual_lines)

    assert parsed == EXPECTED_ENV_VALUES, (
        f"{CURRENT_CERT_ENV} has incorrect certificate metadata values.\n"
        "Expected the active metadata from the legacy PEM comments to be preserved exactly: "
        "lowercase common name, uppercase colon-separated serial, and not_after with Z suffix.\n"
        f"Expected: {EXPECTED_ENV_VALUES!r}\n"
        f"Found: {parsed!r}"
    )

    for forbidden_fragment in ("#", "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----", "MIIBPLACEHOLDER"):
        assert forbidden_fragment not in CURRENT_CERT_ENV.read_text(encoding="utf-8"), (
            f"{CURRENT_CERT_ENV} still contains legacy/comment/PEM material "
            f"({forbidden_fragment!r}); it must be an env-style metadata file only."
        )


def test_legacy_pem_path_is_retired_and_not_a_regular_file():
    """The stale legacy source must not remain available as a regular file."""
    assert not LEGACY_PEM.is_file(), (
        f"Legacy PEM path is still a regular file and has not been retired: {LEGACY_PEM}. "
        "Remove it or otherwise ensure 'test ! -f /home/user/cert-rollout/legacy/live-api.pem' succeeds."
    )

    if LEGACY_PEM.exists() or LEGACY_PEM.is_symlink():
        try:
            resolved = LEGACY_PEM.resolve(strict=True)
        except FileNotFoundError:
            return

        assert not resolved.is_file(), (
            f"Legacy PEM path {LEGACY_PEM} resolves to regular file {resolved}. "
            "The old certificate source must not resolve to a regular file containing stale metadata."
        )

        if resolved.exists() and not resolved.is_dir():
            try:
                content = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                content = ""
            assert "common_name=api.staging.internal" not in content, (
                f"Legacy path {LEGACY_PEM} resolves to a file-like object containing old metadata. "
                "The deployment must not be able to keep validating stale state from the legacy source."
            )


def test_verification_log_exists_with_exact_required_structure():
    """The rollout verification log must prove the new source and retired legacy state."""
    _assert_regular_readable_file(VERIFICATION_LOG, "Rollout verification log")

    actual_lines = _read_lines_tolerating_one_trailing_newline(VERIFICATION_LOG)
    assert actual_lines == EXPECTED_LOG_LINES, (
        f"{VERIFICATION_LOG} does not contain the exact required six verification lines in order.\n"
        "The log must not include extra diagnostics, comments, PEM data, the old source path as "
        "new_source, or legacy_source_retired=no.\n"
        f"Expected lines:\n{EXPECTED_LOG_LINES!r}\n"
        f"Actual lines:\n{actual_lines!r}"
    )


def test_verification_log_values_match_new_env_file_not_legacy_source():
    """The verification log must reflect values read from the new env file."""
    _assert_regular_readable_file(CURRENT_CERT_ENV, "New certificate env source")
    _assert_regular_readable_file(VERIFICATION_LOG, "Rollout verification log")

    env_values = _parse_env_lines(_read_lines_tolerating_one_trailing_newline(CURRENT_CERT_ENV))
    log_values = _parse_env_lines(_read_lines_tolerating_one_trailing_newline(VERIFICATION_LOG))

    assert log_values.get("new_source") == str(CURRENT_CERT_ENV), (
        f"Verification log new_source must point to the new deployment env file {CURRENT_CERT_ENV}, "
        f"not the legacy PEM or another path. Found: {log_values.get('new_source')!r}"
    )
    assert log_values.get("legacy_source_retired") == "yes", (
        f"Verification log must state legacy_source_retired=yes after retiring {LEGACY_PEM}. "
        f"Found: {log_values.get('legacy_source_retired')!r}"
    )

    comparisons = [
        ("verified_common_name", "CERT_COMMON_NAME"),
        ("verified_serial", "CERT_SERIAL"),
        ("verified_not_after", "CERT_NOT_AFTER"),
    ]
    for log_key, env_key in comparisons:
        assert log_values.get(log_key) == env_values.get(env_key), (
            f"Verification log field {log_key} must match {env_key} from {CURRENT_CERT_ENV}.\n"
            f"Log value: {log_values.get(log_key)!r}\n"
            f"Env value: {env_values.get(env_key)!r}"
        )

    assert not LEGACY_PEM.is_file(), (
        f"Verification cannot be accepted while the legacy source remains a regular file: {LEGACY_PEM}"
    )