# test_final_state.py
from pathlib import Path

HOME = Path("/home/user")
REPO = HOME / "credential-rotation"
CONFIG_DIR = REPO / "config"
PATCHES_DIR = REPO / "patches"

SERVICE_ENV = Path("/home/user/credential-rotation/config/service.env")
BACKUP_SERVICE_ENV = Path("/home/user/credential-rotation/config/service.env.pre-rotation")
PATCH_FILE = Path("/home/user/credential-rotation/patches/rotate-api-credentials.patch")
VERIFICATION_LOG = Path("/home/user/credential-rotation/rotation_verification.log")

EXPECTED_FINAL_SERVICE_ENV = """# service.env - production payment gateway integration
SERVICE_NAME=payments-api
SERVICE_PORT=8443
API_BASE_URL=https://payments.example.internal/v1
API_CLIENT_ID=payroll-sync-prod
API_CLIENT_SECRET=rotated_secret_91db6e44
TOKEN_ISSUER=https://issuer.example.internal
TOKEN_AUDIENCE=payments-api
CREDENTIAL_VERSION=2024-09
ROTATION_REQUIRED=false
"""

EXPECTED_PRE_ROTATION_SERVICE_ENV = """# service.env - production payment gateway integration
SERVICE_NAME=payments-api
SERVICE_PORT=8443
API_BASE_URL=https://payments.example.internal/v1
API_CLIENT_ID=payroll-sync-prod
API_CLIENT_SECRET=old_secret_7f9c1a2b
TOKEN_ISSUER=https://issuer.example.internal
TOKEN_AUDIENCE=payments-api
CREDENTIAL_VERSION=2024-03
ROTATION_REQUIRED=true
"""

EXPECTED_PATCH = """--- config/service.env
+++ config/service.env
@@ -3,8 +3,8 @@
 SERVICE_PORT=8443
 API_BASE_URL=https://payments.example.internal/v1
 API_CLIENT_ID=payroll-sync-prod
-API_CLIENT_SECRET=old_secret_7f9c1a2b
+API_CLIENT_SECRET=rotated_secret_91db6e44
 TOKEN_ISSUER=https://issuer.example.internal
 TOKEN_AUDIENCE=payments-api
-CREDENTIAL_VERSION=2024-03
-ROTATION_REQUIRED=true
+CREDENTIAL_VERSION=2024-09
+ROTATION_REQUIRED=false
"""

EXPECTED_VERIFICATION_LOG = """PATCH_APPLIED=yes
SERVICE_ENV_EXISTS=yes
BACKUP_CREATED=yes
ROTATION_STATUS=complete
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_repository_and_required_directories_still_exist():
    assert REPO.exists(), f"Missing repository directory: {REPO}"
    assert REPO.is_dir(), f"Repository path exists but is not a directory: {REPO}"

    assert CONFIG_DIR.exists(), f"Missing config directory: {CONFIG_DIR}"
    assert CONFIG_DIR.is_dir(), f"Config path exists but is not a directory: {CONFIG_DIR}"

    assert PATCHES_DIR.exists(), f"Missing patches directory: {PATCHES_DIR}"
    assert PATCHES_DIR.is_dir(), f"Patches path exists but is not a directory: {PATCHES_DIR}"


def test_service_env_exists_and_matches_exact_rotated_configuration():
    assert SERVICE_ENV.exists(), f"Missing live configuration file after rotation: {SERVICE_ENV}"
    assert SERVICE_ENV.is_file(), f"Live configuration path exists but is not a file: {SERVICE_ENV}"

    actual = read_text(SERVICE_ENV)
    assert actual == EXPECTED_FINAL_SERVICE_ENV, (
        f"{SERVICE_ENV} does not exactly match the required rotated configuration. "
        "The approved patch must be applied cleanly to service.env, changing only the "
        "API_CLIENT_SECRET, CREDENTIAL_VERSION, and ROTATION_REQUIRED values."
    )


def test_service_env_contains_rotated_values_and_no_old_credential_values():
    text = read_text(SERVICE_ENV)

    required_lines = [
        "API_CLIENT_SECRET=rotated_secret_91db6e44\n",
        "CREDENTIAL_VERSION=2024-09\n",
        "ROTATION_REQUIRED=false\n",
    ]
    for line in required_lines:
        assert line in text, f"{SERVICE_ENV} is missing required rotated line: {line.rstrip()}"

    forbidden_lines = [
        "API_CLIENT_SECRET=old_secret_7f9c1a2b\n",
        "CREDENTIAL_VERSION=2024-03\n",
        "ROTATION_REQUIRED=true\n",
    ]
    for line in forbidden_lines:
        assert line not in text, (
            f"{SERVICE_ENV} still contains pre-rotation line that should have been replaced: "
            f"{line.rstrip()}"
        )


def test_service_env_has_no_duplicate_rotated_or_key_lines():
    lines = read_text(SERVICE_ENV).splitlines()

    keys_to_expected_values = {
        "API_CLIENT_SECRET": "API_CLIENT_SECRET=rotated_secret_91db6e44",
        "CREDENTIAL_VERSION": "CREDENTIAL_VERSION=2024-09",
        "ROTATION_REQUIRED": "ROTATION_REQUIRED=false",
    }

    for key, expected_line in keys_to_expected_values.items():
        matching_lines = [line for line in lines if line.startswith(f"{key}=")]
        assert matching_lines == [expected_line], (
            f"{SERVICE_ENV} must contain exactly one {key} line and it must be "
            f"{expected_line!r}. Found: {matching_lines!r}"
        )


def test_pre_rotation_backup_exists_and_matches_original_configuration_exactly():
    assert BACKUP_SERVICE_ENV.exists(), (
        f"Missing required pre-rotation backup file: {BACKUP_SERVICE_ENV}"
    )
    assert BACKUP_SERVICE_ENV.is_file(), (
        f"Backup path exists but is not a file: {BACKUP_SERVICE_ENV}"
    )

    actual = read_text(BACKUP_SERVICE_ENV)
    assert actual == EXPECTED_PRE_ROTATION_SERVICE_ENV, (
        f"{BACKUP_SERVICE_ENV} does not contain the exact original pre-rotation "
        "configuration. The backup must be created before applying the patch, not after."
    )


def test_backup_contains_old_values_and_not_rotated_values():
    text = read_text(BACKUP_SERVICE_ENV)

    assert "API_CLIENT_SECRET=old_secret_7f9c1a2b\n" in text, (
        f"{BACKUP_SERVICE_ENV} must preserve the original API client secret."
    )
    assert "CREDENTIAL_VERSION=2024-03\n" in text, (
        f"{BACKUP_SERVICE_ENV} must preserve the original credential version."
    )
    assert "ROTATION_REQUIRED=true\n" in text, (
        f"{BACKUP_SERVICE_ENV} must preserve the original ROTATION_REQUIRED=true value."
    )

    assert "API_CLIENT_SECRET=rotated_secret_91db6e44" not in text, (
        f"{BACKUP_SERVICE_ENV} contains the rotated secret, which means the backup was "
        "likely created after patching instead of before patching."
    )
    assert "CREDENTIAL_VERSION=2024-09" not in text, (
        f"{BACKUP_SERVICE_ENV} contains the rotated credential version, which should "
        "not be present in the pre-rotation backup."
    )
    assert "ROTATION_REQUIRED=false" not in text, (
        f"{BACKUP_SERVICE_ENV} contains ROTATION_REQUIRED=false, which should not be "
        "present in the pre-rotation backup."
    )


def test_verification_log_exists_and_matches_exact_required_four_lines():
    assert VERIFICATION_LOG.exists(), f"Missing verification log: {VERIFICATION_LOG}"
    assert VERIFICATION_LOG.is_file(), (
        f"Verification log path exists but is not a file: {VERIFICATION_LOG}"
    )

    actual = read_text(VERIFICATION_LOG)
    assert actual == EXPECTED_VERIFICATION_LOG, (
        f"{VERIFICATION_LOG} must contain exactly the required four lines, in order, "
        "with no extra whitespace, blank lines, timestamps, command output, or checksum text."
    )


def test_verification_log_has_exact_required_line_structure():
    raw = read_text(VERIFICATION_LOG)

    assert raw.endswith("\n"), (
        f"{VERIFICATION_LOG} should end with a newline after the fourth required line."
    )

    lines = raw.splitlines()
    expected_lines = [
        "PATCH_APPLIED=yes",
        "SERVICE_ENV_EXISTS=yes",
        "BACKUP_CREATED=yes",
        "ROTATION_STATUS=complete",
    ]
    assert lines == expected_lines, (
        f"{VERIFICATION_LOG} has incorrect lines. Expected exactly {expected_lines!r}; "
        f"found {lines!r}."
    )
    assert len(lines) == 4, (
        f"{VERIFICATION_LOG} must contain exactly four lines; found {len(lines)}."
    )


def test_patch_file_remains_unchanged():
    assert PATCH_FILE.exists(), f"Missing approved patch file: {PATCH_FILE}"
    assert PATCH_FILE.is_file(), f"Patch path exists but is not a file: {PATCH_FILE}"

    actual = read_text(PATCH_FILE)
    assert actual == EXPECTED_PATCH, (
        f"{PATCH_FILE} was changed. The approved patch file must remain exactly unchanged."
    )


def test_no_reject_files_exist_under_repository():
    reject_files = sorted(str(path) for path in REPO.rglob("*.rej"))
    assert reject_files == [], (
        "No .rej reject files should exist under the repository after applying the patch. "
        f"Found: {reject_files}"
    )


def test_final_deliverable_files_are_distinct_and_exact():
    service_text = read_text(SERVICE_ENV)
    backup_text = read_text(BACKUP_SERVICE_ENV)
    log_text = read_text(VERIFICATION_LOG)

    assert service_text == EXPECTED_FINAL_SERVICE_ENV, (
        f"{SERVICE_ENV} is not the exact required rotated final file."
    )
    assert backup_text == EXPECTED_PRE_ROTATION_SERVICE_ENV, (
        f"{BACKUP_SERVICE_ENV} is not the exact required original backup file."
    )
    assert log_text == EXPECTED_VERIFICATION_LOG, (
        f"{VERIFICATION_LOG} is not the exact required verification log."
    )
    assert service_text != backup_text, (
        f"{SERVICE_ENV} and {BACKUP_SERVICE_ENV} should not be identical; the live file "
        "must be rotated while the backup must preserve the original contents."
    )