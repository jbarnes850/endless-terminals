I’m organizing API documentation metadata and need a small validation artifact produced from the files in `/home/user/docs_meta`.

Please inspect the JSON files in `/home/user/docs_meta/source/` and create exactly one output file:

`/home/user/docs_meta/validation_report.json`

The source directory contains:
- `/home/user/docs_meta/source/pages.json`
- `/home/user/docs_meta/source/schema.json`

Use the schema in `schema.json` to validate each page object in `pages.json`. Then use `jq` or equivalent JSON processing to produce a compact JSON report.

The report file must be valid JSON with exactly these top-level keys, in this order:

1. `checked_at`
2. `schema`
3. `summary`
4. `invalid_pages`
5. `slugs_by_section`

The required report format is:

```json
{
  "checked_at": "LOCAL_ISO_8601_TIMESTAMP",
  "schema": {
    "name": "VALUE_FROM_SCHEMA_TITLE",
    "version": "VALUE_FROM_SCHEMA_VERSION"
  },
  "summary": {
    "total_pages": NUMBER,
    "valid_pages": NUMBER,
    "invalid_pages": NUMBER
  },
  "invalid_pages": [
    {
      "slug": "PAGE_SLUG",
      "errors": [
        "HUMAN_READABLE_ERROR"
      ]
    }
  ],
  "slugs_by_section": {
    "SECTION_NAME": [
      "PAGE_SLUG"
    ]
  }
}
```

Requirements:
- `checked_at` must be the current local timestamp in ISO-8601 format including timezone offset, for example `2026-02-14T09:30:00-05:00`.
- `schema.name` must come from the schema title.
- `schema.version` must come from the schema metadata version field.
- Count every page object in `pages.json`.
- A page is valid only if it satisfies the schema in `schema.json`.
- `invalid_pages` must include only invalid pages.
- For each invalid page, list its slug and a non-empty array of readable error strings.
- `slugs_by_section` must include only valid pages.
- Inside each section array, slugs must be sorted alphabetically.
- Section keys must be sorted alphabetically.
- The final JSON file must be compact enough for automated parsing but does not need to be minified.
- Do not modify the source files.

Before you finish, run a verification step that confirms `/home/user/docs_meta/validation_report.json` exists and is parseable JSON. Silence or lack of terminal output from an earlier command is not enough; please verify the final artifact explicitly.
