# test_final_state.py
from pathlib import Path

ROOT = Path("/home/user/api-integration")
REQUEST_ENV = Path("/home/user/api-integration/build/request.env")
VERIFICATION_LOG = Path("/home/user/api-integration/build/verification.log")

EXPECTED_REQUEST_ENV = (
    "API_BASE_URL=https://localhost:9443/mock-api/v1?tenant=dev&trace=true\n"
    "API_TOKEN=local-token_7yF.pilot-42\n"
    "CLIENT_ID=integration-dev-client\n"
    "FEATURE_FLAGS=accounts,balances,transfers\n"
    "REQUEST_TIMEOUT_MS=8500\n"
)

EXPECTED_VERIFICATION_LOG = (
    "artifact_exists=yes\n"
    "line_count=5\n"
    "keys_sorted=yes\n"
    "dotenv_precedence_verified=yes\n"
)

REQUIRED_KEYS = {
    "API_BASE_URL",
    "API_TOKEN",
    "CLIENT_ID",
    "FEATURE_FLAGS",
    "REQUEST_TIMEOUT_MS",
}

FORBIDDEN_NAMES = {
    "LOG_LEVEL",
    "EMPTY_FROM_BASE",
    "DISABLED_FEATURE",
    "LOCAL_EMPTY",
    "EXTRA_HEADER",
}

EXPECTED_VALUES = {
    "API_BASE_URL": "https://localhost:9443/mock-api/v1?tenant=dev&trace=true",
    "API_TOKEN": "local-token_7yF.pilot-42",
    "CLIENT_ID": "integration-dev-client",
    "FEATURE_FLAGS": "accounts,balances,transfers",
    "REQUEST_TIMEOUT_MS": "8500",
}

LOWER_PRIORITY_VALUES_THAT_MUST_NOT_WIN = {
    "API_BASE_URL": "https://sandbox-api.example.test/v1",
    "API_TOKEN": "shared-token-should-not-win",
    "FEATURE_FLAGS": "accounts,balances",
    "REQUEST_TIMEOUT_MS": "3000",
}


def _read_bytes(path: Path) -> bytes:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Required path is not a regular file: {path}"
    return path.read_bytes()


def _decode_utf8(data: bytes, path: Path) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"{path} is not valid UTF-8/plain text: {exc}") from exc


def _parse_request_env(text: str) -> dict[str, str]:
    parsed = {}
    lines = text.splitlines()

    assert len(lines) == 5, (
        f"{REQUEST_ENV} must contain exactly 5 lines; found {len(lines)} lines: {lines!r}"
    )

    for line_number, line in enumerate(lines, start=1):
        assert line, f"{REQUEST_ENV} line {line_number} is blank; blank lines are not allowed"
        assert not line.startswith("export "), (
            f"{REQUEST_ENV} line {line_number} must not start with 'export ': {line!r}"
        )
        assert "=" in line, (
            f"{REQUEST_ENV} line {line_number} is not in exact KEY=value form: {line!r}"
        )

        key, value = line.split("=", 1)

        assert key, f"{REQUEST_ENV} line {line_number} has an empty key: {line!r}"
        assert key == key.strip(), (
            f"{REQUEST_ENV} line {line_number} key has surrounding whitespace: {line!r}"
        )
        assert value == value.strip(), (
            f"{REQUEST_ENV} line {line_number} value has surrounding whitespace: {line!r}"
        )
        assert value != "", (
            f"{REQUEST_ENV} line {line_number} has an empty value for {key}; empty values must be omitted"
        )
        assert not (
            len(value) >= 2
            and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'"))
        ), (
            f"{REQUEST_ENV} line {line_number} still has dotenv quote characters around the value: {line!r}"
        )
        assert key not in parsed, f"{REQUEST_ENV} contains duplicate key {key!r}"
        parsed[key] = value

    return parsed


def test_request_env_exists_as_regular_file_with_exact_expected_contents():
    data = _read_bytes(REQUEST_ENV)

    assert data.endswith(b"\n"), f"{REQUEST_ENV} must end with a trailing newline byte"
    assert data == EXPECTED_REQUEST_ENV.encode("utf-8"), (
        f"{REQUEST_ENV} does not exactly match the required final artifact.\n"
        f"Expected exactly:\n{EXPECTED_REQUEST_ENV!r}\n"
        f"Actual:\n{_decode_utf8(data, REQUEST_ENV)!r}"
    )


def test_request_env_has_only_required_sorted_key_value_lines():
    text = _decode_utf8(_read_bytes(REQUEST_ENV), REQUEST_ENV)
    parsed = _parse_request_env(text)

    actual_keys = list(parsed)
    expected_sorted_keys = sorted(REQUIRED_KEYS)

    assert set(actual_keys) == REQUIRED_KEYS, (
        f"{REQUEST_ENV} must contain exactly the required keys {expected_sorted_keys!r}; "
        f"found {actual_keys!r}"
    )
    assert actual_keys == expected_sorted_keys, (
        f"{REQUEST_ENV} keys must be sorted alphabetically. "
        f"Expected order {expected_sorted_keys!r}; found {actual_keys!r}"
    )

    for forbidden in FORBIDDEN_NAMES:
        assert forbidden not in parsed, (
            f"{REQUEST_ENV} must not include non-request/empty/disabled variable {forbidden!r}"
        )


def test_request_env_values_reflect_dotenv_local_precedence_and_quote_removal():
    text = _decode_utf8(_read_bytes(REQUEST_ENV), REQUEST_ENV)
    parsed = _parse_request_env(text)

    assert parsed == EXPECTED_VALUES, (
        f"{REQUEST_ENV} has incorrect final values after dotenv parsing/precedence.\n"
        f"Expected: {EXPECTED_VALUES!r}\n"
        f"Actual:   {parsed!r}"
    )

    for key, lower_priority_value in LOWER_PRIORITY_VALUES_THAT_MUST_NOT_WIN.items():
        assert parsed.get(key) != lower_priority_value, (
            f"{REQUEST_ENV} uses the lower-priority .env value for {key!r}; "
            f".env.local must override it"
        )

    assert parsed["API_TOKEN"] == "local-token_7yF.pilot-42", (
        "API_TOKEN must come from .env.local with surrounding single quotes removed"
    )
    assert parsed["FEATURE_FLAGS"] == "accounts,balances,transfers", (
        "FEATURE_FLAGS must come from .env.local with surrounding double quotes removed"
    )
    assert parsed["CLIENT_ID"] == "integration-dev-client", (
        "CLIENT_ID should be retained from .env because it is not overridden in .env.local"
    )


def test_request_env_contains_no_comments_malformed_exports_or_forbidden_fragments():
    text = _decode_utf8(_read_bytes(REQUEST_ENV), REQUEST_ENV)

    forbidden_fragments = [
        "export ",
        "#",
        "BROKEN LINE WITHOUT EQUALS",
        "commented-out-token",
        "LOG_LEVEL",
        "EMPTY_FROM_BASE",
        "DISABLED_FEATURE",
        "LOCAL_EMPTY",
        "EXTRA_HEADER",
        '"',
        "'",
        "shared-token-should-not-win",
        "sandbox-api.example.test",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in text, (
            f"{REQUEST_ENV} contains forbidden fragment {fragment!r}; "
            "the artifact should contain only clean KEY=value request variables"
        )


def test_verification_log_exists_with_exact_expected_contents():
    data = _read_bytes(VERIFICATION_LOG)

    assert data.endswith(b"\n"), f"{VERIFICATION_LOG} must end with a trailing newline byte"
    assert data == EXPECTED_VERIFICATION_LOG.encode("utf-8"), (
        f"{VERIFICATION_LOG} does not exactly match the required verification log.\n"
        f"Expected exactly:\n{EXPECTED_VERIFICATION_LOG!r}\n"
        f"Actual:\n{_decode_utf8(data, VERIFICATION_LOG)!r}"
    )


def test_verification_log_is_consistent_with_valid_request_env_state():
    request_data = _read_bytes(REQUEST_ENV)
    request_text = _decode_utf8(request_data, REQUEST_ENV)
    parsed = _parse_request_env(request_text)

    assert request_data == EXPECTED_REQUEST_ENV.encode("utf-8"), (
        f"{VERIFICATION_LOG} may only claim success after {REQUEST_ENV} is exactly correct"
    )

    log_text = _decode_utf8(_read_bytes(VERIFICATION_LOG), VERIFICATION_LOG)
    log_lines = log_text.splitlines()

    assert log_lines == [
        "artifact_exists=yes",
        "line_count=5",
        "keys_sorted=yes",
        "dotenv_precedence_verified=yes",
    ], f"{VERIFICATION_LOG} must contain exactly the four required status lines"

    assert len(parsed) == 5, (
        "verification.log says line_count=5, but request.env does not parse to exactly five variables"
    )
    assert list(parsed) == sorted(parsed), (
        "verification.log says keys_sorted=yes, but request.env keys are not sorted"
    )
    for key, lower_priority_value in LOWER_PRIORITY_VALUES_THAT_MUST_NOT_WIN.items():
        assert parsed[key] != lower_priority_value, (
            "verification.log says dotenv_precedence_verified=yes, but "
            f"{key!r} still has lower-priority value {lower_priority_value!r}"
        )