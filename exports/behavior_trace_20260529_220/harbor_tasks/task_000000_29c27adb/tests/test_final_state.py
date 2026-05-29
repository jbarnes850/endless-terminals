# test_final_state.py
from pathlib import Path
import csv
import io

CSV_PATH = Path("/home/user/encoding_task/processed/customers_utf8.csv")
LOG_PATH = Path("/home/user/encoding_task/processed/verification.log")

EXPECTED_CSV_TEXT = (
    "id,name,city,segment\n"
    "1,André Martin,Montréal,retail\n"
    "2,Björk Gudmundsdóttir,Reykjavík,music\n"
    "3,François Dupont,Québec,enterprise\n"
    "4,Marta Peña,Bogotá,smb\n"
    "5,Jürgen Müller,Zürich,enterprise\n"
    "6,Chloë Dubois,Genève,retail\n"
)

EXPECTED_LOG_TEXT = (
    "utf8_valid: PASS\n"
    "comma_delimited: PASS\n"
    "row_count: PASS\n"
    "accented_text_preserved: PASS\n"
)

EXPECTED_ROWS = [
    ["id", "name", "city", "segment"],
    ["1", "André Martin", "Montréal", "retail"],
    ["2", "Björk Gudmundsdóttir", "Reykjavík", "music"],
    ["3", "François Dupont", "Québec", "enterprise"],
    ["4", "Marta Peña", "Bogotá", "smb"],
    ["5", "Jürgen Müller", "Zürich", "enterprise"],
    ["6", "Chloë Dubois", "Genève", "retail"],
]

MOJIBAKE_STRINGS = [
    "AndrÃ©",
    "MontrÃ©al",
    "BjÃ¶rk",
    "ReykjavÃ­k",
    "FranÃ§ois",
    "QuÃ©bec",
    "PeÃ±a",
    "BogotÃ¡",
    "JÃ¼rgen",
    "MÃ¼ller",
    "ZÃ¼rich",
    "ChloÃ«",
    "GenÃ¨ve",
]


def _read_utf8_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"{path} is not valid UTF-8 text: decode failed at byte "
            f"{exc.start}: {exc.reason}."
        ) from exc


def test_required_output_files_exist_at_exact_paths():
    assert CSV_PATH.exists(), f"Missing required final CSV file: {CSV_PATH}"
    assert CSV_PATH.is_file(), f"Final CSV path exists but is not a regular file: {CSV_PATH}"

    assert LOG_PATH.exists(), f"Missing required verification log: {LOG_PATH}"
    assert LOG_PATH.is_file(), f"Verification log path exists but is not a regular file: {LOG_PATH}"


def test_customers_csv_is_valid_utf8_and_exact_expected_bytes():
    assert CSV_PATH.exists(), f"Missing required final CSV file: {CSV_PATH}"

    actual_bytes = CSV_PATH.read_bytes()
    expected_bytes = EXPECTED_CSV_TEXT.encode("utf-8")

    try:
        actual_text = actual_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"{CSV_PATH} is not valid UTF-8. It must be converted from Latin-1 "
            f"to UTF-8; decode failed at byte {exc.start}: {exc.reason}."
        ) from exc

    assert actual_bytes == expected_bytes, (
        f"{CSV_PATH} does not match the exact expected UTF-8 comma-delimited "
        "content. The file must preserve all field values and accents exactly, "
        "replace semicolon delimiters with commas, contain exactly one header "
        "and six data rows, and end with one newline.\n"
        f"Actual decoded text was:\n{actual_text!r}"
    )


def test_customers_csv_uses_commas_not_semicolons():
    text = _read_utf8_text(CSV_PATH)

    assert ";" not in text, (
        f"{CSV_PATH} still contains semicolons. Encoding conversion alone is "
        "not sufficient; the CSV delimiter must be changed from semicolon to comma."
    )

    lines = text.splitlines()
    missing_commas = [line for line in lines if "," not in line]
    assert not missing_commas, (
        f"{CSV_PATH} has row(s) without comma delimiters: {missing_commas!r}"
    )

    parsed_rows = list(csv.reader(io.StringIO(text), delimiter=","))
    assert parsed_rows == EXPECTED_ROWS, (
        f"{CSV_PATH} is not parsed as the expected comma-delimited CSV rows. "
        f"Parsed rows were: {parsed_rows!r}"
    )


def test_customers_csv_has_exact_header_row_count_and_newline_termination():
    data = CSV_PATH.read_bytes()
    text = _read_utf8_text(CSV_PATH)

    assert data.endswith(b"\n"), f"{CSV_PATH} must end with a newline byte."
    assert not data.endswith(b"\n\n"), (
        f"{CSV_PATH} must end with exactly one trailing newline, not extra blank lines."
    )

    assert text.count("\n") == 7, (
        f"{CSV_PATH} must contain exactly seven newline-terminated records "
        f"(one header and six data rows); found {text.count(chr(10))} newline characters."
    )

    lines = text.splitlines()
    assert len(lines) == 7, (
        f"{CSV_PATH} must contain exactly one header row and six data rows; "
        f"found {len(lines)} rows."
    )
    assert lines[0] == "id,name,city,segment", (
        f"{CSV_PATH} has the wrong header. Expected "
        "'id,name,city,segment' but found {lines[0]!r}."
    )


def test_customers_csv_accents_are_preserved_without_replacement_or_mojibake():
    text = _read_utf8_text(CSV_PATH)

    assert "\ufffd" not in text, (
        f"{CSV_PATH} contains the Unicode replacement character '�', which "
        "means accented text was not decoded or preserved correctly."
    )

    present_mojibake = [bad for bad in MOJIBAKE_STRINGS if bad in text]
    assert not present_mojibake, (
        f"{CSV_PATH} contains mojibake text {present_mojibake!r}. The Latin-1 "
        "source must be decoded correctly before writing UTF-8."
    )

    expected_accented_values = [
        "André Martin",
        "Montréal",
        "Björk Gudmundsdóttir",
        "Reykjavík",
        "François Dupont",
        "Québec",
        "Marta Peña",
        "Bogotá",
        "Jürgen Müller",
        "Zürich",
        "Chloë Dubois",
        "Genève",
    ]
    missing_values = [value for value in expected_accented_values if value not in text]
    assert not missing_values, (
        f"{CSV_PATH} is missing expected accented field value(s): {missing_values!r}"
    )


def test_verification_log_is_valid_utf8_and_exactly_four_pass_lines():
    assert LOG_PATH.exists(), f"Missing required verification log: {LOG_PATH}"

    actual_text = _read_utf8_text(LOG_PATH)

    assert actual_text == EXPECTED_LOG_TEXT, (
        f"{LOG_PATH} must contain exactly the four required verification lines, "
        "all marked PASS and in the required order.\n"
        f"Expected:\n{EXPECTED_LOG_TEXT!r}\n"
        f"Actual:\n{actual_text!r}"
    )


def test_verification_log_reflects_actual_csv_success_state():
    csv_text = _read_utf8_text(CSV_PATH)
    log_text = _read_utf8_text(LOG_PATH)

    actual_checks = {
        "utf8_valid": True,
        "comma_delimited": ";" not in csv_text
        and all("," in line for line in csv_text.splitlines()),
        "row_count": csv_text.endswith("\n")
        and not csv_text.endswith("\n\n")
        and len(csv_text.splitlines()) == 7
        and csv_text.splitlines()[0] == "id,name,city,segment",
        "accented_text_preserved": (
            "\ufffd" not in csv_text
            and not any(bad in csv_text for bad in MOJIBAKE_STRINGS)
            and csv_text == EXPECTED_CSV_TEXT
        ),
    }

    failing_actual_checks = [
        name for name, passed in actual_checks.items() if not passed
    ]
    assert not failing_actual_checks, (
        "The produced CSV does not actually satisfy these verification "
        f"check(s), so the log cannot truthfully be all PASS: {failing_actual_checks!r}"
    )

    expected_lines = [f"{name}: PASS" for name in actual_checks]
    actual_lines = log_text.splitlines()
    assert actual_lines == expected_lines, (
        f"{LOG_PATH} does not truthfully record all four required checks as "
        f"PASS in order. Expected lines {expected_lines!r}, found {actual_lines!r}."
    )