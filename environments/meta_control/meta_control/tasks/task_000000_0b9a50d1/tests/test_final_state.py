# test_final_state.py
from pathlib import Path

BASE = Path("/home/user/cloud-migration")
SERVICES = Path("/home/user/cloud-migration/services")
SELECTED_FILE = Path("/home/user/cloud-migration/selected-service.txt")
AUDIT_FILE = Path("/home/user/cloud-migration/migration_audit.log")
EXPECTED_SELECTED_SERVICE = Path("/home/user/cloud-migration/services/invoice-router")

EXPECTED_SELECTED_CONTENT = "/home/user/cloud-migration/services/invoice-router\n"
EXPECTED_AUDIT_CONTENT = (
    "candidates_total=7\n"
    "passed_metadata=5\n"
    "passed_artifacts=4\n"
    "passed_blockers=2\n"
    "selected_name=invoice-router\n"
    "verification=passed\n"
)

EXPECTED_SERVICE_NAMES = [
    "auth-gateway",
    "billing-api",
    "catalog-worker",
    "invoice-router",
    "metrics-sidecar",
    "orders-api",
    "search-indexer",
]


def _read_text_or_fail(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        raise AssertionError(f"Missing required final file: {path}")
    except IsADirectoryError:
        raise AssertionError(f"Expected final path to be a file, but found a directory: {path}")


def _service_yaml_has(path: Path, key: str, value: str) -> bool:
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return False
    expected_line = f"{key}: {value}"
    return any(line.strip() == expected_line for line in lines)


def _contains_named_file(root: Path, filename: str) -> bool:
    if not root.is_dir():
        return False
    return any(path.is_file() and path.name == filename for path in root.rglob(filename))


def _ready_child_dirs(service_dir: Path) -> list[Path]:
    data_dir = service_dir / "data"
    if not data_dir.is_dir():
        return []
    return sorted(
        child
        for child in data_dir.iterdir()
        if child.is_dir() and (child / "READY").is_file()
    )


def _immediate_service_dirs() -> list[Path]:
    assert SERVICES.is_dir(), f"Missing required services directory: {SERVICES}"
    return sorted(path for path in SERVICES.iterdir() if path.is_dir())


def _derive_candidate_state():
    service_dirs = _immediate_service_dirs()

    passed_metadata = [
        service
        for service in service_dirs
        if (service / "service.yaml").is_file()
        and _service_yaml_has(service / "service.yaml", "environment", "prod")
        and _service_yaml_has(service / "service.yaml", "platform", "k8s")
    ]

    passed_artifacts = [
        service
        for service in passed_metadata
        if (service / "Dockerfile").is_file()
        and (service / "configs" / "prod.env").is_file()
    ]

    passed_blockers = [
        service
        for service in passed_artifacts
        if not _contains_named_file(service, "BLOCK_MIGRATION")
        and not _contains_named_file(service, "legacy.lock")
    ]

    selected = [
        service
        for service in passed_blockers
        if len(_ready_child_dirs(service)) == 1
    ]

    return service_dirs, passed_metadata, passed_artifacts, passed_blockers, selected


def test_required_final_files_exist_and_are_regular_files():
    assert BASE.is_dir(), f"Missing required base directory: {BASE}"

    for path in (SELECTED_FILE, AUDIT_FILE):
        assert path.exists(), f"Required final file was not created: {path}"
        assert path.is_file(), f"Required final path exists but is not a regular file: {path}"


def test_selected_service_file_has_exact_required_contents():
    actual = _read_text_or_fail(SELECTED_FILE)

    assert actual == EXPECTED_SELECTED_CONTENT, (
        f"{SELECTED_FILE} has incorrect contents.\n"
        "It must contain exactly one line with the absolute path to the selected service "
        "directory and one trailing newline, with no labels, quotes, or blank lines.\n"
        f"Expected: {EXPECTED_SELECTED_CONTENT!r}\n"
        f"Actual:   {actual!r}"
    )


def test_migration_audit_log_has_exact_required_contents():
    actual = _read_text_or_fail(AUDIT_FILE)

    assert actual == EXPECTED_AUDIT_CONTENT, (
        f"{AUDIT_FILE} has incorrect contents.\n"
        "It must contain exactly the six required key/value lines, in order, with no "
        "extra spaces and no extra lines.\n"
        f"Expected:\n{EXPECTED_AUDIT_CONTENT!r}\n"
        f"Actual:\n{actual!r}"
    )


def test_selected_path_points_to_the_only_eligible_service_directory():
    selected_text = _read_text_or_fail(SELECTED_FILE).strip("\n")

    assert selected_text == str(EXPECTED_SELECTED_SERVICE), (
        f"{SELECTED_FILE} selects the wrong service.\n"
        f"Expected selected service: {EXPECTED_SELECTED_SERVICE}\n"
        f"Actual selected service:   {selected_text}"
    )

    selected_path = Path(selected_text)
    assert selected_path.is_absolute(), (
        f"Selected service path must be absolute, but got: {selected_text}"
    )
    assert selected_path.is_dir(), (
        f"Selected service path does not exist as a directory: {selected_path}"
    )


def test_filesystem_still_has_expected_immediate_service_directories():
    actual_names = sorted(path.name for path in _immediate_service_dirs())
    expected_names = sorted(EXPECTED_SERVICE_NAMES)

    assert actual_names == expected_names, (
        f"Immediate service directories under {SERVICES} changed unexpectedly.\n"
        "The task required selecting a service and writing final files, not renaming, "
        "deleting, or adding service directories.\n"
        f"Expected: {expected_names}\n"
        f"Actual:   {actual_names}"
    )


def test_derived_candidate_counts_match_final_audit_log():
    service_dirs, passed_metadata, passed_artifacts, passed_blockers, selected = (
        _derive_candidate_state()
    )

    expected_sets = {
        "all candidates": EXPECTED_SERVICE_NAMES,
        "passed metadata": [
            "billing-api",
            "catalog-worker",
            "invoice-router",
            "orders-api",
            "search-indexer",
        ],
        "passed artifacts": [
            "catalog-worker",
            "invoice-router",
            "orders-api",
            "search-indexer",
        ],
        "passed blockers": [
            "invoice-router",
            "orders-api",
        ],
        "eligible selected": [
            "invoice-router",
        ],
    }
    actual_sets = {
        "all candidates": [p.name for p in service_dirs],
        "passed metadata": [p.name for p in passed_metadata],
        "passed artifacts": [p.name for p in passed_artifacts],
        "passed blockers": [p.name for p in passed_blockers],
        "eligible selected": [p.name for p in selected],
    }

    for label, expected in expected_sets.items():
        actual = actual_sets[label]
        assert actual == expected, (
            f"Derived {label} set is wrong, so the migration evidence is not correct.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )

    expected_audit_lines = {
        "candidates_total": str(len(service_dirs)),
        "passed_metadata": str(len(passed_metadata)),
        "passed_artifacts": str(len(passed_artifacts)),
        "passed_blockers": str(len(passed_blockers)),
        "selected_name": selected[0].name if len(selected) == 1 else "",
        "verification": "passed",
    }

    actual_audit_lines = {}
    for line in _read_text_or_fail(AUDIT_FILE).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            actual_audit_lines[key] = value

    assert actual_audit_lines == expected_audit_lines, (
        f"{AUDIT_FILE} does not match the candidate state derived from the filesystem.\n"
        f"Expected parsed key/values: {expected_audit_lines}\n"
        f"Actual parsed key/values:   {actual_audit_lines}"
    )


def test_invoice_router_satisfies_all_eligibility_conditions():
    service = EXPECTED_SELECTED_SERVICE

    assert (service / "service.yaml").is_file(), (
        f"Selected service is missing service.yaml: {service / 'service.yaml'}"
    )
    assert _service_yaml_has(service / "service.yaml", "environment", "prod"), (
        f"Selected service.yaml does not declare environment: prod: {service / 'service.yaml'}"
    )
    assert _service_yaml_has(service / "service.yaml", "platform", "k8s"), (
        f"Selected service.yaml does not declare platform: k8s: {service / 'service.yaml'}"
    )
    assert (service / "Dockerfile").is_file(), (
        f"Selected service is missing top-level Dockerfile: {service / 'Dockerfile'}"
    )
    assert (service / "configs" / "prod.env").is_file(), (
        f"Selected service is missing configs/prod.env: {service / 'configs' / 'prod.env'}"
    )
    assert not _contains_named_file(service, "BLOCK_MIGRATION"), (
        f"Selected service must not contain BLOCK_MIGRATION anywhere under: {service}"
    )
    assert not _contains_named_file(service, "legacy.lock"), (
        f"Selected service must not contain legacy.lock anywhere under: {service}"
    )

    ready_dirs = _ready_child_dirs(service)
    assert ready_dirs == [service / "data" / "cutover-batch"], (
        "Selected service must have exactly one immediate data child directory "
        "containing READY.\n"
        f"Expected: {[service / 'data' / 'cutover-batch']}\n"
        f"Actual:   {ready_dirs}"
    )


def test_near_miss_services_were_not_selected():
    selected = _read_text_or_fail(SELECTED_FILE)

    near_miss_paths = [
        "/home/user/cloud-migration/services/billing-api\n",
        "/home/user/cloud-migration/services/catalog-worker\n",
        "/home/user/cloud-migration/services/orders-api\n",
        "/home/user/cloud-migration/services/search-indexer\n",
    ]

    assert selected not in near_miss_paths, (
        f"{SELECTED_FILE} selected a near-miss service rather than invoice-router. "
        f"Actual contents: {selected!r}"
    )