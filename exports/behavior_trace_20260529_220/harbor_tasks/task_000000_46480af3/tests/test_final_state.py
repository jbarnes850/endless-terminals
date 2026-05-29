# test_final_state.py
from pathlib import Path
import os
import stat


HOME = Path("/home/user")
SUPPORT_DIR = Path("/home/user/support_tickets")
SOURCE_FILE = Path("/home/user/support_tickets/ticket_export.tsv")
ESCALATION_SHEET = Path("/home/user/support_tickets/escalation_sheet.tsv")
BUILD_LOG = Path("/home/user/support_tickets/escalation_build.log")

EXPECTED_SOURCE_CONTENT = (
    "TicketID\tOpenedAt\tRequester\tDept\tAssetTag\tHostname\tIssue\tSerial\tLastSeen\tOwnerEmail\tStatus\tPriority\n"
    "TCK-4101\t2026-02-03 08:17\tMina Patel\tFinance\tAT-00931\tfin-lap-014\tVPN client fails\tSN8K21F\t2026-02-03 08:10\tmina.patel@example.com\tOpen\tHigh\n"
    "TCK-4102\t2026-02-03 08:31\tOwen Briggs\tSales\tAT-00442\tsls-dsk-022\tMonitor flicker\tSN1P77Q\t2026-02-02 17:55\towen.briggs@example.com\tClosed\tMedium\n"
    "TCK-4103\t2026-02-03 08:49\tLena Zhou\tEngineering\tAT-01007\teng-lap-108\tDisk encryption prompt loop\tSN4D88M\t2026-02-03 08:42\tlena.zhou@example.com\tWaiting\tCritical\n"
    "TCK-4104\t2026-02-03 09:04\tCarlos Nunez\tSupport\tAT-00219\tsup-dsk-009\tKeyboard replacement\tSN6H45T\t2026-02-01 13:12\tcarlos.nunez@example.com\tOpen\tLow\n"
    "TCK-4105\t2026-02-03 09:22\tAsha Rao\tFinance\tAT-00944\tfin-lap-021\tEmail archive missing\tSN2B90L\t2026-02-03 09:18\tasha.rao@example.com\tOpen\tMedium\n"
    "TCK-4106\t2026-02-03 09:39\tPeter Holm\tLegal\tAT-00618\tleg-lap-033\tUnable to print\tSN3C11R\t2026-02-03 09:01\tpeter.holm@example.com\tPending\tHigh\n"
    "TCK-4107\t2026-02-03 09:58\tNora Kim\tHR\tAT-00752\thr-lap-017\tPassword reset loop\tSN9X02A\t2026-02-03 09:53\tnora.kim@example.com\tWaiting\tHigh\n"
    "TCK-4108\t2026-02-03 10:11\tEli Turner\tEngineering\tAT-01018\teng-wks-044\tBuild tools corrupted\tSN7V34E\t2026-02-03 10:07\teli.turner@example.com\tOpen\tCritical\n"
    "TCK-4109\t2026-02-03 10:26\tFatima Noor\tSales\tAT-00467\tsls-lap-031\tCRM shortcut missing\tSN5J66K\t2026-02-03 09:41\tfatima.noor@example.com\tWaiting\tLow\n"
    "TCK-4110\t2026-02-03 10:44\tBen Archer\tOperations\tAT-00385\tops-dsk-012\tShared drive access denied\tSN0L13Z\t2026-02-03 10:40\tben.archer@example.com\tOpen\tHigh\n"
)

EXPECTED_ESCALATION_CONTENT = (
    "TicketID\tAssetTag\tHostname\tOwnerEmail\tPriority\tStatus\tEscalationNote\n"
    "TCK-4101\tAT-00931\tfin-lap-014\tmina.patel@example.com\tHigh\tOpen\tEMAIL_OWNER\n"
    "TCK-4103\tAT-01007\teng-lap-108\tlena.zhou@example.com\tCritical\tWaiting\tCALL_OWNER\n"
    "TCK-4105\tAT-00944\tfin-lap-021\tasha.rao@example.com\tMedium\tOpen\tQUEUE_REVIEW\n"
    "TCK-4107\tAT-00752\thr-lap-017\tnora.kim@example.com\tHigh\tWaiting\tEMAIL_OWNER\n"
    "TCK-4108\tAT-01018\teng-wks-044\teli.turner@example.com\tCritical\tOpen\tCALL_OWNER\n"
    "TCK-4110\tAT-00385\tops-dsk-012\tben.archer@example.com\tHigh\tOpen\tEMAIL_OWNER\n"
)

EXPECTED_ESCALATION_CONTENT_NO_FINAL_NEWLINE = EXPECTED_ESCALATION_CONTENT.rstrip("\n")

EXPECTED_LOG_CONTENT = (
    "source=/home/user/support_tickets/ticket_export.tsv\n"
    "output=/home/user/support_tickets/escalation_sheet.tsv\n"
    "columns=7\n"
    "filters=status_open_or_waiting_and_priority_not_low\n"
    "order=preserved\n"
    "verified=manual\n"
)

EXPECTED_LOG_CONTENT_NO_FINAL_NEWLINE = EXPECTED_LOG_CONTENT.rstrip("\n")

EXPECTED_HEADER = "TicketID\tAssetTag\tHostname\tOwnerEmail\tPriority\tStatus\tEscalationNote"
EXPECTED_TICKET_ORDER = ["TCK-4101", "TCK-4103", "TCK-4105", "TCK-4107", "TCK-4108", "TCK-4110"]
FORBIDDEN_TICKET_IDS = {
    "TCK-4102": "Closed status must be excluded",
    "TCK-4104": "Low priority must be excluded even though status is Open",
    "TCK-4106": "Pending status must be excluded",
    "TCK-4109": "Low priority must be excluded even though status is Waiting",
}

SOURCE_BY_TICKET = {
    "TCK-4101": {
        "AssetTag": "AT-00931",
        "Hostname": "fin-lap-014",
        "OwnerEmail": "mina.patel@example.com",
        "Status": "Open",
        "Priority": "High",
    },
    "TCK-4103": {
        "AssetTag": "AT-01007",
        "Hostname": "eng-lap-108",
        "OwnerEmail": "lena.zhou@example.com",
        "Status": "Waiting",
        "Priority": "Critical",
    },
    "TCK-4105": {
        "AssetTag": "AT-00944",
        "Hostname": "fin-lap-021",
        "OwnerEmail": "asha.rao@example.com",
        "Status": "Open",
        "Priority": "Medium",
    },
    "TCK-4107": {
        "AssetTag": "AT-00752",
        "Hostname": "hr-lap-017",
        "OwnerEmail": "nora.kim@example.com",
        "Status": "Waiting",
        "Priority": "High",
    },
    "TCK-4108": {
        "AssetTag": "AT-01018",
        "Hostname": "eng-wks-044",
        "OwnerEmail": "eli.turner@example.com",
        "Status": "Open",
        "Priority": "Critical",
    },
    "TCK-4110": {
        "AssetTag": "AT-00385",
        "Hostname": "ops-dsk-012",
        "OwnerEmail": "ben.archer@example.com",
        "Status": "Open",
        "Priority": "High",
    },
}

NOTE_BY_PRIORITY = {
    "Critical": "CALL_OWNER",
    "High": "EMAIL_OWNER",
    "Medium": "QUEUE_REVIEW",
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _logical_lines_allowing_final_newline(path: Path):
    text = _read_text(path)
    return text.splitlines()


def test_support_directory_still_exists_and_is_writable():
    assert SUPPORT_DIR.exists(), f"Required directory is missing: {SUPPORT_DIR}"
    assert SUPPORT_DIR.is_dir(), f"Required path exists but is not a directory: {SUPPORT_DIR}"

    mode = SUPPORT_DIR.stat().st_mode
    assert bool(mode & stat.S_IWUSR), (
        f"Directory is not writable by its owner; expected /home/user to be able to write to: {SUPPORT_DIR}"
    )
    assert os.access(SUPPORT_DIR, os.W_OK), (
        f"Current test process cannot write to required directory: {SUPPORT_DIR}"
    )


def test_source_export_remains_byte_for_byte_unchanged():
    assert SOURCE_FILE.exists(), f"Source export is missing; it must not be deleted or moved: {SOURCE_FILE}"
    assert SOURCE_FILE.is_file(), f"Source export path is not a regular file: {SOURCE_FILE}"

    actual = SOURCE_FILE.read_bytes()
    expected = EXPECTED_SOURCE_CONTENT.encode("utf-8")
    assert actual == expected, (
        f"Source export was modified, but task required it to remain byte-for-byte unchanged: {SOURCE_FILE}"
    )


def test_escalation_sheet_exists_and_is_regular_file():
    assert ESCALATION_SHEET.exists(), (
        f"Missing required cleaned escalation sheet: {ESCALATION_SHEET}"
    )
    assert ESCALATION_SHEET.is_file(), (
        f"Escalation sheet path exists but is not a regular file: {ESCALATION_SHEET}"
    )


def test_escalation_sheet_exact_contents_match_expected():
    assert ESCALATION_SHEET.exists(), f"Cannot validate missing file: {ESCALATION_SHEET}"

    actual = _read_text(ESCALATION_SHEET)
    valid_variants = {EXPECTED_ESCALATION_CONTENT, EXPECTED_ESCALATION_CONTENT_NO_FINAL_NEWLINE}
    assert actual in valid_variants, (
        f"Escalation sheet does not exactly match the required TSV contents: {ESCALATION_SHEET}\n"
        "It must contain the exact header, filtered rows in source order, generated EscalationNote values, "
        "literal tab delimiters, and no extra blank records."
    )


def test_escalation_sheet_header_delimiters_and_column_count():
    assert ESCALATION_SHEET.exists(), f"Cannot validate missing file: {ESCALATION_SHEET}"
    text = _read_text(ESCALATION_SHEET)
    lines = text.splitlines()

    assert lines, f"Escalation sheet is empty; expected header plus 6 ticket rows: {ESCALATION_SHEET}"
    assert lines[0] == EXPECTED_HEADER, (
        f"Escalation sheet header is wrong. Expected exactly:\n{EXPECTED_HEADER!r}\n"
        f"Found:\n{lines[0]!r}"
    )

    assert "," not in lines[0], (
        f"Escalation sheet appears comma-delimited or contains commas in the header; expected literal tabs: {ESCALATION_SHEET}"
    )

    assert len(lines) == 7, (
        f"Escalation sheet must contain exactly 7 non-empty records: 1 header and 6 ticket rows. "
        f"Found {len(lines)} records in {ESCALATION_SHEET}"
    )

    for line_number, line in enumerate(lines, start=1):
        assert line.strip() != "", (
            f"Escalation sheet contains an extra blank record at line {line_number}: {ESCALATION_SHEET}"
        )
        assert "\t" in line, (
            f"Line {line_number} is not tab-delimited; expected literal tab characters: {line!r}"
        )
        fields = line.split("\t")
        assert len(fields) == 7, (
            f"Line {line_number} must have exactly 7 tab-separated fields, found {len(fields)}: {line!r}"
        )


def test_escalation_sheet_no_extra_blank_line_or_empty_record_at_end():
    assert ESCALATION_SHEET.exists(), f"Cannot validate missing file: {ESCALATION_SHEET}"
    content = _read_text(ESCALATION_SHEET)

    assert not content.endswith("\n\n"), (
        f"Escalation sheet has an extra blank line at the end; only a single trailing newline is acceptable: "
        f"{ESCALATION_SHEET}"
    )
    assert "" not in content.splitlines(), (
        f"Escalation sheet contains an empty/blank record; no blank lines are allowed: {ESCALATION_SHEET}"
    )


def test_escalation_sheet_filtering_excludes_wrong_statuses_and_low_priority():
    assert ESCALATION_SHEET.exists(), f"Cannot validate missing file: {ESCALATION_SHEET}"
    lines = _logical_lines_allowing_final_newline(ESCALATION_SHEET)
    data_lines = lines[1:]
    ticket_ids = [line.split("\t")[0] for line in data_lines]

    assert ticket_ids == EXPECTED_TICKET_ORDER, (
        f"Escalation sheet has the wrong ticket set or row order. Expected exactly: {EXPECTED_TICKET_ORDER}; "
        f"found: {ticket_ids}"
    )

    for forbidden_id, reason in FORBIDDEN_TICKET_IDS.items():
        assert forbidden_id not in ticket_ids, (
            f"Escalation sheet incorrectly includes {forbidden_id}: {reason}."
        )

    for line_number, line in enumerate(data_lines, start=2):
        fields = line.split("\t")
        ticket_id, asset_tag, hostname, owner_email, priority, status, note = fields
        assert status in {"Open", "Waiting"}, (
            f"Line {line_number} includes ticket {ticket_id} with invalid Status={status!r}; "
            "only exactly 'Open' or exactly 'Waiting' are allowed."
        )
        assert priority != "Low", (
            f"Line {line_number} includes ticket {ticket_id} with Priority='Low', which must be excluded."
        )


def test_escalation_sheet_first_six_columns_match_source_fields_exactly():
    assert ESCALATION_SHEET.exists(), f"Cannot validate missing file: {ESCALATION_SHEET}"
    lines = _logical_lines_allowing_final_newline(ESCALATION_SHEET)

    for line_number, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        ticket_id, asset_tag, hostname, owner_email, priority, status, note = fields
        assert ticket_id in SOURCE_BY_TICKET, (
            f"Unexpected TicketID {ticket_id!r} appears on line {line_number}; filtering or source extraction is wrong."
        )
        expected = SOURCE_BY_TICKET[ticket_id]

        assert asset_tag == expected["AssetTag"], (
            f"Line {line_number} ticket {ticket_id} has wrong AssetTag. "
            f"Expected {expected['AssetTag']!r}, found {asset_tag!r}."
        )
        assert hostname == expected["Hostname"], (
            f"Line {line_number} ticket {ticket_id} has wrong Hostname. "
            f"Expected {expected['Hostname']!r}, found {hostname!r}."
        )
        assert owner_email == expected["OwnerEmail"], (
            f"Line {line_number} ticket {ticket_id} has wrong OwnerEmail. "
            f"Expected {expected['OwnerEmail']!r}, found {owner_email!r}."
        )
        assert priority == expected["Priority"], (
            f"Line {line_number} ticket {ticket_id} has wrong Priority. "
            f"Expected {expected['Priority']!r}, found {priority!r}. "
            "Check that Priority and Status were not swapped."
        )
        assert status == expected["Status"], (
            f"Line {line_number} ticket {ticket_id} has wrong Status. "
            f"Expected {expected['Status']!r}, found {status!r}. "
            "Check that Priority and Status were not swapped."
        )


def test_escalation_notes_match_priority_mapping_exactly():
    assert ESCALATION_SHEET.exists(), f"Cannot validate missing file: {ESCALATION_SHEET}"
    lines = _logical_lines_allowing_final_newline(ESCALATION_SHEET)

    for line_number, line in enumerate(lines[1:], start=2):
        ticket_id, asset_tag, hostname, owner_email, priority, status, note = line.split("\t")
        expected_note = NOTE_BY_PRIORITY.get(priority)
        assert expected_note is not None, (
            f"Line {line_number} ticket {ticket_id} has unexpected Priority={priority!r}; "
            "expected one of Critical, High, or Medium after filtering."
        )
        assert note == expected_note, (
            f"Line {line_number} ticket {ticket_id} has wrong EscalationNote for Priority={priority!r}. "
            f"Expected {expected_note!r}, found {note!r}."
        )


def test_verification_log_exists_and_is_regular_file():
    assert BUILD_LOG.exists(), f"Missing required verification log: {BUILD_LOG}"
    assert BUILD_LOG.is_file(), f"Verification log path exists but is not a regular file: {BUILD_LOG}"


def test_verification_log_exact_six_lines_and_no_extra_text():
    assert BUILD_LOG.exists(), f"Cannot validate missing file: {BUILD_LOG}"

    actual = _read_text(BUILD_LOG)
    valid_variants = {EXPECTED_LOG_CONTENT, EXPECTED_LOG_CONTENT_NO_FINAL_NEWLINE}
    assert actual in valid_variants, (
        f"Verification log does not exactly match the required 6-line format: {BUILD_LOG}\n"
        "It must contain only the specified source/output/columns/filters/order/verified lines, "
        "with no timestamps, counts, command transcript, diagnostics, or extra blank lines."
    )

    lines = actual.splitlines()
    assert len(lines) == 6, (
        f"Verification log must contain exactly 6 lines; found {len(lines)} lines in {BUILD_LOG}"
    )
    assert lines == EXPECTED_LOG_CONTENT_NO_FINAL_NEWLINE.splitlines(), (
        f"Verification log lines are not exactly the required lines in the required order: {BUILD_LOG}"
    )
    assert "" not in lines, (
        f"Verification log contains an extra blank line; no blank lines are allowed: {BUILD_LOG}"
    )