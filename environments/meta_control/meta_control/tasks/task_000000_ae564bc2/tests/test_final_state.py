# test_final_state.py
from pathlib import Path
import stat

BASE_DIR = Path("/home/user/cloud-migration")
CURRENT_DIR = Path("/home/user/cloud-migration/current")
CURRENT_ENV = Path("/home/user/cloud-migration/current/.env")
LEGACY_ENV = Path("/home/user/cloud-migration/legacy/.env")
MIGRATION_LOG = Path("/home/user/cloud-migration/migration-check.log")

EXPECTED_CURRENT_ENV_BYTES = (
    b"BILLING_API_ENDPOINT=https://billing.internal.example.com/v2\n"
    b"BILLING_REGION=us-east-2\n"
    b"FEATURE_FLAG_LEDGER_V2=true\n"
)

EXPECTED_CURRENT_ENV_LINES = [
    "BILLING_API_ENDPOINT=https://billing.internal.example.com/v2",
    "BILLING_REGION=us-east-2",
    "FEATURE_FLAG_LEDGER_V2=true",
]

EXPECTED_VARIABLE_NAMES_IN_ORDER = [
    "BILLING_API_ENDPOINT",
    "BILLING_REGION",
    "FEATURE_FLAG_LEDGER_V2",
]

EXPECTED_LOG_BYTES = (
    b"active_env=/home/user/cloud-migration/current/.env\n"
    b"legacy_env_retired=yes\n"
    b"endpoint_version=v2\n"
    b"ledger_v2_enabled=yes\n"
)


def _mode_description(path: Path) -> str:
    try:
        st = path.lstat()
    except FileNotFoundError:
        return "missing"
    mode = st.st_mode
    if stat.S_ISREG(mode):
        return "regular file"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISCHR(mode):
        return "character device"
    if stat.S_ISBLK(mode):
        return "block device"
    return f"unknown file type mode={oct(mode)}"


def _read_bytes_for_message(path: Path, limit: int = 500) -> str:
    try:
        data = path.read_bytes()
    except Exception as exc:
        return f"<could not read {path}: {exc!r}>"
    suffix = b"" if len(data) <= limit else b"...<truncated>"
    return repr(data[:limit] + suffix)


def test_current_directory_exists_as_directory():
    assert CURRENT_DIR.exists(), f"Required directory {CURRENT_DIR} is missing"
    assert CURRENT_DIR.is_dir(), (
        f"Required path {CURRENT_DIR} must be a directory, "
        f"but it is a {_mode_description(CURRENT_DIR)}"
    )


def test_current_dotenv_exists_as_regular_file():
    assert CURRENT_ENV.exists(), f"Required active dotenv file {CURRENT_ENV} is missing"
    assert CURRENT_ENV.is_file(), (
        f"Required active dotenv path {CURRENT_ENV} must be a regular file, "
        f"but it is a {_mode_description(CURRENT_ENV)}"
    )


def test_current_dotenv_has_exact_expected_bytes():
    actual = CURRENT_ENV.read_bytes()
    assert actual == EXPECTED_CURRENT_ENV_BYTES, (
        f"{CURRENT_ENV} must contain exactly the migrated dotenv bytes, including "
        f"line order and final newline.\n\n"
        f"Expected bytes:\n{EXPECTED_CURRENT_ENV_BYTES!r}\n\n"
        f"Actual bytes:\n{actual!r}"
    )


def test_current_dotenv_contains_only_required_variable_names_in_order():
    text = CURRENT_ENV.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines == EXPECTED_CURRENT_ENV_LINES, (
        f"{CURRENT_ENV} must contain exactly three assignment lines with no comments, "
        f"blank lines, quotes, export prefixes, or extra variables.\n"
        f"Expected lines: {EXPECTED_CURRENT_ENV_LINES!r}\n"
        f"Actual lines:   {lines!r}"
    )

    actual_names = [line.split("=", 1)[0] for line in lines]
    assert actual_names == EXPECTED_VARIABLE_NAMES_IN_ORDER, (
        f"{CURRENT_ENV} must use exactly these variable names in this order: "
        f"{EXPECTED_VARIABLE_NAMES_IN_ORDER!r}. Actual names were {actual_names!r}"
    )


def test_current_dotenv_preserves_region_and_updates_endpoint_and_feature_flag():
    env = {}
    for line in CURRENT_ENV.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        assert sep == "=", f"Line {line!r} in {CURRENT_ENV} is not a valid KEY=value assignment"
        env[key] = value

    assert env.get("BILLING_REGION") == "us-east-2", (
        f"{CURRENT_ENV} must preserve production region BILLING_REGION=us-east-2; "
        f"actual value was {env.get('BILLING_REGION')!r}"
    )
    assert env.get("BILLING_API_ENDPOINT") == "https://billing.internal.example.com/v2", (
        f"{CURRENT_ENV} must point BILLING_API_ENDPOINT to the v2 endpoint "
        f"https://billing.internal.example.com/v2; actual value was "
        f"{env.get('BILLING_API_ENDPOINT')!r}"
    )
    assert env.get("FEATURE_FLAG_LEDGER_V2") == "true", (
        f"{CURRENT_ENV} must enable FEATURE_FLAG_LEDGER_V2=true; "
        f"actual value was {env.get('FEATURE_FLAG_LEDGER_V2')!r}"
    )

    joined = CURRENT_ENV.read_text(encoding="utf-8")
    assert "/v1" not in joined, (
        f"{CURRENT_ENV} must not retain the stale /v1 endpoint suffix. "
        f"Actual content was {_read_bytes_for_message(CURRENT_ENV)}"
    )
    assert "FEATURE_FLAG_LEDGER_V2=false" not in joined, (
        f"{CURRENT_ENV} must not retain stale disabled ledger flag. "
        f"Actual content was {_read_bytes_for_message(CURRENT_ENV)}"
    )


def test_legacy_dotenv_is_retired_and_not_a_usable_complete_dotenv():
    if not LEGACY_ENV.exists():
        return

    assert not LEGACY_ENV.is_file() or not _legacy_file_contains_complete_dotenv(LEGACY_ENV), (
        f"{LEGACY_ENV} must be retired so it cannot be mistaken for the active "
        f"configuration. It may be removed, changed to a non-regular file, or left as "
        f"a regular file only if it does not contain all three active dotenv "
        f"assignment lines. Actual legacy state is {_mode_description(LEGACY_ENV)} "
        f"with content {_read_bytes_for_message(LEGACY_ENV)}"
    )


def _legacy_file_contains_complete_dotenv(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False

    assignment_names = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].lstrip()
        key, sep, _value = stripped.partition("=")
        if sep == "=":
            assignment_names.add(key.strip())

    required = {
        "BILLING_API_ENDPOINT",
        "BILLING_REGION",
        "FEATURE_FLAG_LEDGER_V2",
    }
    return required.issubset(assignment_names)


def test_migration_check_log_exists_as_regular_file():
    assert MIGRATION_LOG.exists(), f"Required verification log {MIGRATION_LOG} is missing"
    assert MIGRATION_LOG.is_file(), (
        f"Required verification log {MIGRATION_LOG} must be a regular file, "
        f"but it is a {_mode_description(MIGRATION_LOG)}"
    )


def test_migration_check_log_has_exact_expected_bytes():
    actual = MIGRATION_LOG.read_bytes()
    assert actual == EXPECTED_LOG_BYTES, (
        f"{MIGRATION_LOG} must contain exactly the required four verification lines, "
        f"in order, with a final newline and no extra whitespace.\n\n"
        f"Expected bytes:\n{EXPECTED_LOG_BYTES!r}\n\n"
        f"Actual bytes:\n{actual!r}"
    )


def test_verification_log_reports_current_env_not_legacy_env():
    text = MIGRATION_LOG.read_text(encoding="utf-8")
    assert "active_env=/home/user/cloud-migration/current/.env\n" in text, (
        f"{MIGRATION_LOG} must report the active env as "
        f"/home/user/cloud-migration/current/.env"
    )
    assert "active_env=/home/user/cloud-migration/legacy/.env" not in text, (
        f"{MIGRATION_LOG} must not report the retired legacy dotenv as active. "
        f"Actual log content was {_read_bytes_for_message(MIGRATION_LOG)}"
    )