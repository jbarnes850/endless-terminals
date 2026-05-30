# test_final_state.py
import json
import re
from pathlib import Path

import pytest


BASE = Path("/home/user/docs_meta")
SOURCE = Path("/home/user/docs_meta/source")
SCHEMA_PATH = Path("/home/user/docs_meta/source/schema.json")
PAGES_PATH = Path("/home/user/docs_meta/source/pages.json")
REPORT_PATH = Path("/home/user/docs_meta/validation_report.json")

EXPECTED_SCHEMA_TEXT = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Documentation Page Metadata",
  "x-metadata": {
    "version": "1.4.2"
  },
  "type": "object",
  "required": ["slug", "title", "section", "status", "word_count"],
  "additionalProperties": false,
  "properties": {
    "slug": {
      "type": "string",
      "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"
    },
    "title": {
      "type": "string",
      "minLength": 5
    },
    "section": {
      "type": "string",
      "enum": ["getting-started", "reference", "tutorials"]
    },
    "status": {
      "type": "string",
      "enum": ["draft", "review", "published"]
    },
    "word_count": {
      "type": "integer",
      "minimum": 100
    }
  }
}
"""

EXPECTED_PAGES_TEXT = """[
  {
    "slug": "installation-guide",
    "title": "Installation Guide",
    "section": "getting-started",
    "status": "published",
    "word_count": 840
  },
  {
    "slug": "quickstart",
    "title": "Quickstart Tutorial",
    "section": "tutorials",
    "status": "review",
    "word_count": 620
  },
  {
    "slug": "api-auth",
    "title": "API Authentication",
    "section": "reference",
    "status": "published",
    "word_count": 510
  },
  {
    "slug": "bad Slug",
    "title": "Bad Slug Example",
    "section": "reference",
    "status": "draft",
    "word_count": 210
  },
  {
    "slug": "tiny-note",
    "title": "Tiny",
    "section": "tutorials",
    "status": "published",
    "word_count": 42
  },
  {
    "slug": "orphan-page",
    "title": "Orphan Page",
    "section": "appendix",
    "status": "draft",
    "word_count": 300
  }
]
"""

EXPECTED_TOP_LEVEL_KEYS = [
    "checked_at",
    "schema",
    "summary",
    "invalid_pages",
    "slugs_by_section",
]

EXPECTED_SCHEMA_REPORT = {
    "name": "Documentation Page Metadata",
    "version": "1.4.2",
}

EXPECTED_SUMMARY = {
    "total_pages": 6,
    "valid_pages": 3,
    "invalid_pages": 3,
}

EXPECTED_SLUGS_BY_SECTION = {
    "getting-started": ["installation-guide"],
    "reference": ["api-auth"],
    "tutorials": ["quickstart"],
}

EXPECTED_INVALID_SLUGS = ["bad Slug", "tiny-note", "orphan-page"]

TIMESTAMP_WITH_TZ_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"[+-][0-9]{2}:[0-9]{2}$"
)


@pytest.fixture(scope="module")
def report_text():
    assert REPORT_PATH.exists(), (
        "Expected final output file is missing: "
        "/home/user/docs_meta/validation_report.json"
    )
    assert REPORT_PATH.is_file(), (
        "Expected final output path exists but is not a regular file: "
        "/home/user/docs_meta/validation_report.json"
    )
    return REPORT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report(report_text):
    try:
        parsed = json.loads(report_text)
    except json.JSONDecodeError as exc:
        pytest.fail(
            "/home/user/docs_meta/validation_report.json is not parseable JSON: "
            f"{exc}"
        )
    assert isinstance(parsed, dict), (
        "/home/user/docs_meta/validation_report.json must contain a JSON object "
        "at the top level"
    )
    return parsed


def test_source_files_remain_unchanged_byte_for_byte():
    assert SCHEMA_PATH.exists(), "Source schema file is missing: /home/user/docs_meta/source/schema.json"
    assert PAGES_PATH.exists(), "Source pages file is missing: /home/user/docs_meta/source/pages.json"

    actual_schema = SCHEMA_PATH.read_text(encoding="utf-8")
    actual_pages = PAGES_PATH.read_text(encoding="utf-8")

    assert actual_schema == EXPECTED_SCHEMA_TEXT, (
        "Source file /home/user/docs_meta/source/schema.json was modified; "
        "the task required source files to remain unchanged byte-for-byte"
    )
    assert actual_pages == EXPECTED_PAGES_TEXT, (
        "Source file /home/user/docs_meta/source/pages.json was modified; "
        "the task required source files to remain unchanged byte-for-byte"
    )


def test_no_unexpected_output_files_in_docs_meta_root():
    assert BASE.exists(), "Required directory is missing: /home/user/docs_meta"
    assert SOURCE.exists(), "Required source directory is missing: /home/user/docs_meta/source"

    allowed = {
        "/home/user/docs_meta/source",
        "/home/user/docs_meta/validation_report.json",
    }
    actual = {str(path) for path in BASE.iterdir()}
    unexpected = sorted(actual - allowed)

    assert not unexpected, (
        "Unexpected extra item(s) found in /home/user/docs_meta. "
        "The task required exactly one output file, "
        "/home/user/docs_meta/validation_report.json. "
        f"Unexpected item(s): {unexpected}"
    )


def test_report_has_exact_top_level_keys_in_required_order(report):
    actual_keys = list(report.keys())
    assert actual_keys == EXPECTED_TOP_LEVEL_KEYS, (
        "Report top-level keys are wrong or in the wrong order. "
        f"Expected exactly {EXPECTED_TOP_LEVEL_KEYS}, got {actual_keys}"
    )


def test_checked_at_is_iso_8601_local_timestamp_with_timezone(report):
    checked_at = report.get("checked_at")
    assert isinstance(checked_at, str), (
        "Report field 'checked_at' must be a string timestamp"
    )
    assert TIMESTAMP_WITH_TZ_RE.match(checked_at), (
        "Report field 'checked_at' must match ISO-8601 local timestamp format "
        "including timezone offset, e.g. 2026-02-14T09:30:00-05:00. "
        f"Got: {checked_at!r}"
    )


def test_schema_section_matches_source_schema_title_and_version(report):
    assert report.get("schema") == EXPECTED_SCHEMA_REPORT, (
        "Report field 'schema' is incorrect. It must exactly contain the schema "
        "title and x-metadata version from /home/user/docs_meta/source/schema.json. "
        f"Expected {EXPECTED_SCHEMA_REPORT}, got {report.get('schema')!r}"
    )


def test_summary_counts_all_pages_and_validity_correctly(report):
    assert report.get("summary") == EXPECTED_SUMMARY, (
        "Report field 'summary' is incorrect. The pages.json source has 6 total "
        "pages, of which 3 satisfy the schema and 3 are invalid. "
        f"Expected {EXPECTED_SUMMARY}, got {report.get('summary')!r}"
    )


def test_invalid_pages_contains_exact_invalid_slugs_with_required_shape(report):
    invalid_pages = report.get("invalid_pages")
    assert isinstance(invalid_pages, list), (
        "Report field 'invalid_pages' must be an array"
    )
    assert len(invalid_pages) == 3, (
        "Report field 'invalid_pages' must contain exactly 3 invalid page objects "
        f"for slugs {EXPECTED_INVALID_SLUGS}; got {len(invalid_pages)} entries"
    )

    actual_slugs = []
    for index, entry in enumerate(invalid_pages):
        assert isinstance(entry, dict), (
            f"invalid_pages[{index}] must be an object, got {type(entry).__name__}"
        )
        assert list(entry.keys()) == ["slug", "errors"], (
            f"invalid_pages[{index}] must have exactly keys ['slug', 'errors'] "
            f"in that order; got {list(entry.keys())}"
        )

        slug = entry["slug"]
        errors = entry["errors"]
        actual_slugs.append(slug)

        assert slug in EXPECTED_INVALID_SLUGS, (
            f"invalid_pages[{index}] has unexpected slug {slug!r}; expected only "
            f"{EXPECTED_INVALID_SLUGS}"
        )
        assert isinstance(errors, list), (
            f"invalid_pages entry for slug {slug!r} must have 'errors' as an array"
        )
        assert errors, (
            f"invalid_pages entry for slug {slug!r} must include at least one "
            "human-readable schema validation error"
        )
        assert all(isinstance(error, str) and error.strip() for error in errors), (
            f"invalid_pages entry for slug {slug!r} must have only non-empty "
            f"string errors; got {errors!r}"
        )

    assert actual_slugs == EXPECTED_INVALID_SLUGS, (
        "Report field 'invalid_pages' must contain exactly the invalid page slugs "
        "from pages.json, preferably in source order. "
        f"Expected {EXPECTED_INVALID_SLUGS}, got {actual_slugs}"
    )


def test_invalid_page_errors_truthfully_correspond_to_schema_violations(report):
    invalid_by_slug = {entry["slug"]: entry["errors"] for entry in report["invalid_pages"]}

    bad_slug_errors = " ".join(invalid_by_slug["bad Slug"]).lower()
    assert any(token in bad_slug_errors for token in ["pattern", "match", "regex", "slug"]), (
        "Errors for invalid page slug 'bad Slug' must describe the slug pattern "
        f"violation; got {invalid_by_slug['bad Slug']!r}"
    )

    tiny_note_errors = " ".join(invalid_by_slug["tiny-note"]).lower()
    assert any(token in tiny_note_errors for token in ["minlength", "minimum", "length", "short", "100", "42", "word_count", "title"]), (
        "Errors for invalid page slug 'tiny-note' must describe at least one real "
        "schema violation: title minLength and/or word_count minimum. "
        f"Got {invalid_by_slug['tiny-note']!r}"
    )

    orphan_errors = " ".join(invalid_by_slug["orphan-page"]).lower()
    assert any(token in orphan_errors for token in ["enum", "appendix", "section", "allowed"]), (
        "Errors for invalid page slug 'orphan-page' must describe the section enum "
        f"violation; got {invalid_by_slug['orphan-page']!r}"
    )


def test_slugs_by_section_contains_only_valid_pages_sorted_by_section_and_slug(report):
    slugs_by_section = report.get("slugs_by_section")

    assert slugs_by_section == EXPECTED_SLUGS_BY_SECTION, (
        "Report field 'slugs_by_section' is incorrect. It must include only valid "
        "pages, section keys sorted alphabetically, and slugs within each section "
        "sorted alphabetically. "
        f"Expected {EXPECTED_SLUGS_BY_SECTION}, got {slugs_by_section!r}"
    )
    assert list(slugs_by_section.keys()) == sorted(slugs_by_section.keys()), (
        "Section keys in 'slugs_by_section' must be sorted alphabetically"
    )
    for section, slugs in slugs_by_section.items():
        assert slugs == sorted(slugs), (
            f"Slugs for section {section!r} must be sorted alphabetically; got {slugs!r}"
        )

    flattened_valid_slugs = {
        slug for slugs in slugs_by_section.values() for slug in slugs
    }
    invalid_slugs_present = flattened_valid_slugs.intersection(EXPECTED_INVALID_SLUGS)
    assert not invalid_slugs_present, (
        "Invalid pages must not appear in 'slugs_by_section'. "
        f"Found invalid slug(s): {sorted(invalid_slugs_present)}"
    )