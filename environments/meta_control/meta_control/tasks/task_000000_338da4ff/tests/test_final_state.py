# test_final_state.py
import posixpath
import tarfile
import zipfile
from pathlib import Path

import pytest


BASE = Path("/home/user/ml_data_prep")
RAW_DIR = Path("/home/user/ml_data_prep/raw")
DELIVERABLES_DIR = Path("/home/user/ml_data_prep/deliverables")

SOURCE_ARCHIVE = Path("/home/user/ml_data_prep/raw/image_labels_batch.tar.gz")
FINAL_ZIP = Path("/home/user/ml_data_prep/deliverables/training_data_ready.zip")
VERIFICATION_LOG = Path("/home/user/ml_data_prep/deliverables/verification.log")

EXPECTED_ZIP_FILES = [
    "images/img_001.txt",
    "images/img_002.txt",
    "labels/labels.csv",
]

SOURCE_TO_ZIP_PATH = {
    "batch_export/images/img_001.txt": "images/img_001.txt",
    "batch_export/images/img_002.txt": "images/img_002.txt",
    "batch_export/labels/labels.csv": "labels/labels.csv",
}

EXPECTED_SOURCE_CONTENTS = {
    "batch_export/images/img_001.txt": (
        b"pixel_summary=cat_sample_001\n"
        b"width=224\n"
        b"height=224\n"
        b"split=train\n"
    ),
    "batch_export/images/img_002.txt": (
        b"pixel_summary=dog_sample_002\n"
        b"width=224\n"
        b"height=224\n"
        b"split=train\n"
    ),
    "batch_export/labels/labels.csv": (
        b"filename,label\n"
        b"img_001.txt,cat\n"
        b"img_002.txt,dog\n"
    ),
}

FORBIDDEN_ZIP_ENTRIES = {
    "batch_export/",
    "batch_export/images/img_001.txt",
    "batch_export/images/img_002.txt",
    "batch_export/labels/labels.csv",
    "README.md",
    "batch_export/README.md",
    "tmp/cache_note.txt",
    "batch_export/tmp/cache_note.txt",
}

EXPECTED_VERIFICATION_LOG = (
    "archive=/home/user/ml_data_prep/deliverables/training_data_ready.zip\n"
    "status=verified\n"
    "entries=3\n"
)


def _assert_absolute_path(path: Path) -> None:
    assert path.is_absolute(), f"Test bug: expected absolute path, got {path!s}"


def _read_expected_source_bytes_from_archive() -> dict[str, bytes]:
    _assert_absolute_path(SOURCE_ARCHIVE)

    assert SOURCE_ARCHIVE.exists(), (
        f"Original source archive is missing: {SOURCE_ARCHIVE}. "
        "The task required this archive to remain present and unmodified."
    )
    assert SOURCE_ARCHIVE.is_file(), (
        f"Original source archive path is not a regular file: {SOURCE_ARCHIVE}"
    )

    try:
        with tarfile.open(SOURCE_ARCHIVE, mode="r:gz") as tf:
            actual = {}
            for source_name, expected_bytes in EXPECTED_SOURCE_CONTENTS.items():
                try:
                    member = tf.getmember(source_name)
                except KeyError:
                    pytest.fail(
                        "Original source archive no longer contains required file "
                        f"{source_name!r}. The source archive must not be modified."
                    )

                extracted = tf.extractfile(member)
                assert extracted is not None, (
                    f"Could not read {source_name!r} from original source archive."
                )
                actual_bytes = extracted.read()
                assert actual_bytes == expected_bytes, (
                    "Original source archive contents differ from the expected setup. "
                    "The task required the original archive not to be modified.\n"
                    f"Archive: {SOURCE_ARCHIVE}\n"
                    f"Entry: {source_name}\n"
                    f"Expected bytes: {expected_bytes!r}\n"
                    f"Actual bytes:   {actual_bytes!r}"
                )
                actual[SOURCE_TO_ZIP_PATH[source_name]] = actual_bytes
            return actual
    except tarfile.TarError as exc:
        pytest.fail(
            f"Original source archive is not a valid gzip-compressed tar archive: "
            f"{SOURCE_ARCHIVE}: {exc}"
        )


@pytest.fixture(scope="module")
def expected_zip_contents_from_source() -> dict[str, bytes]:
    return _read_expected_source_bytes_from_archive()


@pytest.fixture(scope="module")
def zip_infos() -> list[zipfile.ZipInfo]:
    _assert_absolute_path(FINAL_ZIP)

    assert FINAL_ZIP.exists(), (
        "Final training-data ZIP was not created at the required absolute path: "
        f"{FINAL_ZIP}"
    )
    assert FINAL_ZIP.is_file(), (
        f"Final ZIP path exists but is not a regular file: {FINAL_ZIP}"
    )
    assert FINAL_ZIP.stat().st_size > 0, (
        f"Final ZIP exists but is empty: {FINAL_ZIP}"
    )

    try:
        with zipfile.ZipFile(FINAL_ZIP, mode="r") as zf:
            corrupt_member = zf.testzip()
            assert corrupt_member is None, (
                f"Final ZIP is corrupt; first bad member reported by testzip(): "
                f"{corrupt_member!r}"
            )
            return zf.infolist()
    except zipfile.BadZipFile as exc:
        pytest.fail(f"Final deliverable is not a valid ZIP archive: {FINAL_ZIP}: {exc}")


def test_final_zip_exists_and_is_valid_zip(zip_infos: list[zipfile.ZipInfo]):
    assert zip_infos, (
        f"Final ZIP is valid but contains no entries: {FINAL_ZIP}. "
        f"It must contain exactly {EXPECTED_ZIP_FILES}."
    )


def test_final_zip_contains_exactly_three_required_regular_files_and_no_directories(
    zip_infos: list[zipfile.ZipInfo],
):
    names = [info.filename for info in zip_infos]
    directory_entries = [name for name in names if name.endswith("/")]

    assert not directory_entries, (
        "Final ZIP must not contain directory entries; it must contain only the "
        f"three required regular file entries. Found directories: {directory_entries}"
    )

    assert len(names) == 3, (
        "Final ZIP must contain exactly three entries and no extras.\n"
        f"Expected entries: {EXPECTED_ZIP_FILES}\n"
        f"Actual entries:   {names}"
    )

    assert sorted(names) == sorted(EXPECTED_ZIP_FILES), (
        "Final ZIP entries are not exactly the required top-level paths.\n"
        f"Expected entries: {sorted(EXPECTED_ZIP_FILES)}\n"
        f"Actual entries:   {sorted(names)}"
    )

    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    assert not duplicate_names, (
        f"Final ZIP contains duplicate entries, which is not allowed: {duplicate_names}"
    )


def test_final_zip_entries_are_not_absolute_or_parent_traversal_paths(
    zip_infos: list[zipfile.ZipInfo],
):
    names = [info.filename for info in zip_infos]

    absolute_names = [name for name in names if name.startswith("/")]
    traversal_names = [
        name
        for name in names
        if any(part == ".." for part in posixpath.normpath(name).split("/"))
    ]

    assert not absolute_names, (
        f"Final ZIP must not contain absolute paths. Found: {absolute_names}"
    )
    assert not traversal_names, (
        "Final ZIP must not contain parent-directory traversal paths. "
        f"Found: {traversal_names}"
    )


def test_final_zip_does_not_include_source_parent_directory_or_excluded_files(
    zip_infos: list[zipfile.ZipInfo],
):
    names = set(info.filename for info in zip_infos)
    forbidden_present = sorted(names.intersection(FORBIDDEN_ZIP_ENTRIES))

    assert not forbidden_present, (
        "Final ZIP includes forbidden entries from the source export or excluded "
        f"artifacts. These must be omitted: {forbidden_present}"
    )

    batch_export_prefixed = sorted(
        name for name in names if name == "batch_export" or name.startswith("batch_export/")
    )
    assert not batch_export_prefixed, (
        "Final ZIP must place images/ and labels/ at the archive top level, not "
        f"under batch_export/. Found: {batch_export_prefixed}"
    )


def test_final_zip_file_contents_match_source_archive_exactly(
    expected_zip_contents_from_source: dict[str, bytes],
):
    with zipfile.ZipFile(FINAL_ZIP, mode="r") as zf:
        for zip_path, expected_bytes in expected_zip_contents_from_source.items():
            try:
                actual_bytes = zf.read(zip_path)
            except KeyError:
                pytest.fail(
                    f"Final ZIP is missing required entry {zip_path!r}. "
                    f"Archive checked: {FINAL_ZIP}"
                )

            assert actual_bytes == expected_bytes, (
                "Final ZIP entry content does not match the corresponding source "
                "archive file exactly.\n"
                f"ZIP archive: {FINAL_ZIP}\n"
                f"Entry: {zip_path}\n"
                f"Expected bytes: {expected_bytes!r}\n"
                f"Actual bytes:   {actual_bytes!r}"
            )


def test_verification_log_exists_and_has_exact_required_format():
    _assert_absolute_path(VERIFICATION_LOG)

    assert VERIFICATION_LOG.exists(), (
        "Verification log was not created at the required absolute path: "
        f"{VERIFICATION_LOG}"
    )
    assert VERIFICATION_LOG.is_file(), (
        f"Verification log path exists but is not a regular file: {VERIFICATION_LOG}"
    )

    actual_text = VERIFICATION_LOG.read_text(encoding="utf-8")

    allowed_without_final_newline = EXPECTED_VERIFICATION_LOG.rstrip("\n")
    assert actual_text in {EXPECTED_VERIFICATION_LOG, allowed_without_final_newline}, (
        "Verification log does not have the exact required three-line format.\n"
        f"Expected exactly either:\n{EXPECTED_VERIFICATION_LOG!r}\n"
        f"or without the final trailing newline:\n{allowed_without_final_newline!r}\n"
        f"Actual content:\n{actual_text!r}"
    )

    actual_lines = actual_text.splitlines()
    expected_lines = EXPECTED_VERIFICATION_LOG.splitlines()
    assert actual_lines == expected_lines, (
        "Verification log lines are incorrect.\n"
        f"Expected lines: {expected_lines}\n"
        f"Actual lines:   {actual_lines}"
    )


def test_verification_log_status_is_consistent_with_actual_zip_entries(
    zip_infos: list[zipfile.ZipInfo],
):
    actual_log = VERIFICATION_LOG.read_text(encoding="utf-8")
    names = [info.filename for info in zip_infos if not info.filename.endswith("/")]

    assert "status=verified" in actual_log.splitlines(), (
        "Verification log must contain status=verified after the archive has been "
        "checked."
    )
    assert len(names) == 3 and sorted(names) == sorted(EXPECTED_ZIP_FILES), (
        "verification.log claims the archive is verified, but the actual ZIP "
        "entries are not exactly the required three files.\n"
        f"Expected entries: {sorted(EXPECTED_ZIP_FILES)}\n"
        f"Actual regular entries: {sorted(names)}"
    )