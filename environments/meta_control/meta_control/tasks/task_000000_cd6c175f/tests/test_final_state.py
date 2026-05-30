# test_final_state.py
from pathlib import Path
import ipaddress
import stat

CURRENT_ZONE = Path("/home/user/cm-dns/current/dns-overrides.zone")
LEGACY_HOSTS = Path("/home/user/cm-dns/legacy/hosts.static")
VERIFICATION_LOG = Path("/home/user/cm-dns/current/resolution-verification.log")

EXPECTED_ZONE_CONTENT = (
    "api.internal.test A 10.44.8.21\n"
    "app.internal.test A 10.44.8.20\n"
    "cache.internal.test A 10.44.8.22\n"
    "db.internal.test A 10.44.8.25\n"
)

EXPECTED_RECORDS = [
    "api.internal.test A 10.44.8.21",
    "app.internal.test A 10.44.8.20",
    "cache.internal.test A 10.44.8.22",
    "db.internal.test A 10.44.8.25",
]

EXPECTED_HOST_TO_IP = {
    "api.internal.test": "10.44.8.21",
    "app.internal.test": "10.44.8.20",
    "cache.internal.test": "10.44.8.22",
    "db.internal.test": "10.44.8.25",
}

EXPECTED_LOG_CONTENT = (
    "source_of_truth=/home/user/cm-dns/current/dns-overrides.zone\n"
    "legacy_regular_file=absent\n"
    "record_count=4\n"
    "first_record=api.internal.test A 10.44.8.21\n"
    "last_record=db.internal.test A 10.44.8.25\n"
)


def _read_zone_text():
    assert CURRENT_ZONE.exists(), (
        f"Authoritative DNS override file is missing: {CURRENT_ZONE}"
    )
    assert CURRENT_ZONE.is_file(), (
        f"Authoritative DNS override path exists but is not a regular file: "
        f"{CURRENT_ZONE}"
    )
    return CURRENT_ZONE.read_text(encoding="utf-8")


def _zone_lines():
    return _read_zone_text().splitlines()


def test_authoritative_dns_overrides_zone_exists_as_regular_file():
    assert CURRENT_ZONE.exists(), (
        f"Final source of truth must exist at absolute path {CURRENT_ZONE}"
    )
    assert CURRENT_ZONE.is_file(), (
        f"Final source of truth must be a regular file at {CURRENT_ZONE}"
    )


def test_authoritative_dns_overrides_zone_has_exact_expected_contents():
    actual = _read_zone_text()
    assert actual == EXPECTED_ZONE_CONTENT, (
        f"{CURRENT_ZONE} does not exactly match the required final migrated "
        "DNS override contents. It must replace the stale placeholder and "
        "contain only the four migrated canonical hostname records sorted by "
        "hostname.\n"
        f"Expected:\n{EXPECTED_ZONE_CONTENT!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_zone_contains_only_active_records_with_strict_three_field_format():
    lines = _zone_lines()

    assert lines, f"{CURRENT_ZONE} must not be empty."
    assert all(line.strip() == line for line in lines), (
        f"{CURRENT_ZONE} contains leading or trailing whitespace on one or "
        "more lines; each line must be exactly 'HOSTNAME A IPV4_ADDRESS'."
    )
    assert all(line for line in lines), (
        f"{CURRENT_ZONE} contains blank lines; blank lines are not allowed."
    )

    for line in lines:
        assert "#" not in line, (
            f"{CURRENT_ZONE} contains a comment or comment marker, which is "
            f"not allowed in the final authoritative file: {line!r}"
        )
        assert "\t" not in line, (
            f"{CURRENT_ZONE} contains tab whitespace; fields must be separated "
            f"by a single space only: {line!r}"
        )
        assert "  " not in line, (
            f"{CURRENT_ZONE} contains extra whitespace; fields must be "
            f"separated by a single space only: {line!r}"
        )

        fields = line.split(" ")
        assert len(fields) == 3, (
            f"Bad record in {CURRENT_ZONE}: {line!r}. Each line must have "
            "exactly three fields: HOSTNAME A IPV4_ADDRESS."
        )

        hostname, record_type, ip_address = fields
        assert record_type == "A", (
            f"Bad record type in {CURRENT_ZONE}: {line!r}. The middle field "
            "must be exactly 'A'."
        )

        try:
            parsed_ip = ipaddress.ip_address(ip_address)
        except ValueError as exc:
            raise AssertionError(
                f"Bad IPv4 address in {CURRENT_ZONE}: {line!r}. "
                f"{ip_address!r} is not a valid IP address."
            ) from exc

        assert parsed_ip.version == 4, (
            f"Bad IP version in {CURRENT_ZONE}: {line!r}. The address must be "
            "IPv4."
        )

        assert hostname.endswith(".internal.test"), (
            f"Unexpected hostname in {CURRENT_ZONE}: {hostname!r}. The final "
            "records should use canonical hostnames from the legacy source."
        )


def test_zone_records_are_sorted_lexicographically_by_hostname():
    lines = _zone_lines()
    hostnames = [line.split(" ")[0] for line in lines]
    assert hostnames == sorted(hostnames), (
        f"Records in {CURRENT_ZONE} are not sorted lexicographically by "
        f"hostname. Actual order: {hostnames!r}; expected order: "
        f"{sorted(hostnames)!r}."
    )


def test_zone_preserves_legacy_hostname_to_ip_semantics_and_drops_aliases():
    lines = _zone_lines()
    parsed = {}
    for line in lines:
        fields = line.split(" ")
        assert len(fields) == 3, (
            f"Cannot validate migrated semantics because this line is not in "
            f"strict DNS override format: {line!r}"
        )
        hostname, record_type, ip_address = fields
        assert record_type == "A", (
            f"Cannot validate migrated semantics because this line does not "
            f"use an A record: {line!r}"
        )
        parsed[hostname] = ip_address

    assert parsed == EXPECTED_HOST_TO_IP, (
        f"{CURRENT_ZONE} does not preserve the exact canonical hostname-to-IP "
        "mappings from the legacy hosts file, or it contains extra/missing "
        "records.\n"
        f"Expected mapping: {EXPECTED_HOST_TO_IP!r}\n"
        f"Actual mapping: {parsed!r}"
    )

    forbidden_alias_records = {
        "api A 10.44.8.21",
        "app A 10.44.8.20",
        "cache A 10.44.8.22",
        "db A 10.44.8.25",
    }
    actual_lines = set(lines)
    present_aliases = sorted(actual_lines & forbidden_alias_records)
    assert not present_aliases, (
        f"{CURRENT_ZONE} includes aliases that should have been dropped: "
        + ", ".join(present_aliases)
    )


def test_stale_current_record_and_initial_comments_are_absent():
    actual = _read_zone_text()

    assert "stale.internal.test A 192.0.2.99" not in actual, (
        f"{CURRENT_ZONE} still contains the stale placeholder record. The "
        "current file must be replaced with migrated active records, not "
        "appended to."
    )
    assert "managed by config-manager v2" not in actual, (
        f"{CURRENT_ZONE} still contains the initial placeholder comment. "
        "Comments are not allowed in the final authoritative file."
    )
    assert "TODO: migrate active host records" not in actual, (
        f"{CURRENT_ZONE} still contains the initial TODO comment. Comments "
        "are not allowed in the final authoritative file."
    )


def test_legacy_hosts_static_is_retired_and_not_regular_file():
    if LEGACY_HOSTS.exists():
        mode = LEGACY_HOSTS.lstat().st_mode
        assert not stat.S_ISREG(mode), (
            f"Legacy source {LEGACY_HOSTS} still exists as a regular file. "
            "It must be retired so it cannot be mistaken for the authoritative "
            "source."
        )
    else:
        assert not LEGACY_HOSTS.is_file(), (
            f"Legacy source {LEGACY_HOSTS} must not exist as a regular file."
        )


def test_verification_log_exists_as_regular_file():
    assert VERIFICATION_LOG.exists(), (
        f"Required verification log is missing: {VERIFICATION_LOG}"
    )
    assert VERIFICATION_LOG.is_file(), (
        f"Verification log path exists but is not a regular file: "
        f"{VERIFICATION_LOG}"
    )


def test_verification_log_has_exact_expected_contents():
    actual = VERIFICATION_LOG.read_text(encoding="utf-8")
    assert actual == EXPECTED_LOG_CONTENT, (
        f"{VERIFICATION_LOG} does not exactly match the required verification "
        "log. The log must contain exactly five key/value lines computed from "
        f"the final authoritative file {CURRENT_ZONE}, with no extra lines.\n"
        f"Expected:\n{EXPECTED_LOG_CONTENT!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_verification_log_is_consistent_with_final_zone_file():
    zone_lines = _zone_lines()
    log_lines = VERIFICATION_LOG.read_text(encoding="utf-8").splitlines()

    expected_log_lines_from_zone = [
        f"source_of_truth={CURRENT_ZONE}",
        "legacy_regular_file=absent",
        f"record_count={len(zone_lines)}",
        f"first_record={zone_lines[0]}",
        f"last_record={zone_lines[-1]}",
    ]

    assert log_lines == expected_log_lines_from_zone, (
        f"{VERIFICATION_LOG} is not consistent with the final authoritative "
        f"zone file {CURRENT_ZONE}. It must be computed from the current DNS "
        "override file, not from the retired legacy file.\n"
        f"Expected from zone file: {expected_log_lines_from_zone!r}\n"
        f"Actual log lines: {log_lines!r}"
    )


def test_final_state_has_no_legacy_hosts_style_records_in_authoritative_zone():
    for line in _zone_lines():
        fields = line.split(" ")
        assert fields[1] == "A", (
            f"{CURRENT_ZONE} appears to contain a legacy /etc/hosts-style "
            f"record instead of DNS override format: {line!r}"
        )
        assert not fields[0][0].isdigit(), (
            f"{CURRENT_ZONE} appears to start a record with an IP address, "
            f"which indicates legacy /etc/hosts-style format was copied "
            f"without conversion: {line!r}"
        )