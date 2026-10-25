import importlib.util
import io
import os
import sys
from pathlib import Path
from urllib.parse import quote

import pytest


LOCKED_DETAIL = "Test data cannot be changed after the report has been submitted for review"


def _backend_root() -> Path:
    for directory in Path(__file__).resolve().parents:
        if (directory / "app.py").is_file():
            return directory
    raise RuntimeError("Could not find the backend app.py for the Stage 3 workflow-lock tests")


BACKEND_ROOT = _backend_root()
APP_PATH = BACKEND_ROOT / "app.py"


def _sqlite_url(database_path: Path) -> str:
    return f"sqlite:///{quote(database_path.resolve().as_posix(), safe='/:')}"


@pytest.fixture(scope="session")
def workflow_backend(tmp_path_factory):
    database_path = tmp_path_factory.mktemp("stage3_workflow_lock_db") / "workflow.sqlite"
    previous_database_url = os.environ.get("DATABASE_URL")
    had_database_url = "DATABASE_URL" in os.environ
    previous_secret_key = os.environ.get("SECRET_KEY")
    had_secret_key = "SECRET_KEY" in os.environ
    previous_demo_mode = os.environ.get("NAWI_DEMO_MODE")
    had_demo_mode = "NAWI_DEMO_MODE" in os.environ
    previous_session_cookie_secure = os.environ.get("NAWI_SESSION_COOKIE_SECURE")
    had_session_cookie_secure = "NAWI_SESSION_COOKIE_SECURE" in os.environ
    previous_data_dir = os.environ.get("NAWI_DATA_DIR")
    had_data_dir = "NAWI_DATA_DIR" in os.environ
    previous_sys_path = list(sys.path)

    os.environ["DATABASE_URL"] = _sqlite_url(database_path)
    os.environ["SECRET_KEY"] = "stage3-rbac-test-secret"
    os.environ["NAWI_DEMO_MODE"] = "0"
    os.environ["NAWI_SESSION_COOKIE_SECURE"] = "0"
    os.environ["NAWI_DATA_DIR"] = str(database_path.parent)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    spec = importlib.util.spec_from_file_location("app", APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        # Use the repository's real rules package. This test provides no rule
        # modules and does not replace any module in sys.modules.
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous_sys_path
        if had_database_url:
            os.environ["DATABASE_URL"] = previous_database_url  # type: ignore[arg-type]
        else:
            os.environ.pop("DATABASE_URL", None)
        if had_secret_key:
            os.environ["SECRET_KEY"] = previous_secret_key  # type: ignore[arg-type]
        else:
            os.environ.pop("SECRET_KEY", None)
        if had_demo_mode:
            os.environ["NAWI_DEMO_MODE"] = previous_demo_mode  # type: ignore[arg-type]
        else:
            os.environ.pop("NAWI_DEMO_MODE", None)
        if had_session_cookie_secure:
            os.environ["NAWI_SESSION_COOKIE_SECURE"] = previous_session_cookie_secure  # type: ignore[arg-type]
        else:
            os.environ.pop("NAWI_SESSION_COOKIE_SECURE", None)
        if had_data_dir:
            os.environ["NAWI_DATA_DIR"] = previous_data_dir  # type: ignore[arg-type]
        else:
            os.environ.pop("NAWI_DATA_DIR", None)

    storage_dir = tmp_path_factory.mktemp("stage3_workflow_lock_storage")
    module.UPLOAD = str(storage_dir / "uploads")
    module.REPORTS = str(storage_dir / "reports")
    module.PRODUCT_IMAGES = str(storage_dir / "uploads" / "products")
    module.EVIDENCE = str(storage_dir / "uploads" / "evidence")
    for directory in (module.UPLOAD, module.REPORTS, module.PRODUCT_IMAGES, module.EVIDENCE):
        Path(directory).mkdir(parents=True, exist_ok=True)

    try:
        module.app.config.update(TESTING=True)
        yield module
    finally:
        with module.app.app_context():
            module.db.session.remove()
            module.db.drop_all()
            module.db.engine.dispose()
        database_path.unlink(missing_ok=True)


@pytest.fixture()
def workflow_data(workflow_backend):
    backend = workflow_backend
    with backend.app.app_context():
        backend.db.session.remove()
        backend.db.drop_all()
        backend.db.create_all()

        users = {}
        for username, role in (
            ("admin", "Admin"),
            ("tester-a", "Tester"),
            ("tester-b", "Tester"),
            ("reviewer", "Reviewer"),
            ("manufacturer", "Manufacturer"),
        ):
            user = backend.User(
                username=username,
                role=role,
                password_hash=backend.generate_password_hash("password"),
            )
            backend.db.session.add(user)
            users[username] = user
        backend.db.session.flush()

        instrument = backend.Instrument(
            manufacturer="NAWI",
            model="Workflow scale",
            serial_number="WORKFLOW-001",
            accuracy_class="III",
            max_capacity=30000,
            min_capacity=100,
            e=5,
            d=0.5,
            unit="g",
        )
        backend.db.session.add(instrument)
        backend.db.session.flush()

        reports = {}
        for key, owner, status, temperature in (
            ("a_draft", users["tester-a"].id, "In Progress", 18.0),
            ("a_review", users["tester-a"].id, "Review", 19.0),
            ("a_completed", users["tester-a"].id, "Completed", 20.0),
            ("b_review", users["tester-b"].id, "Review", 21.0),
        ):
            report = backend.Report(
                report_number=f"WORKFLOW-{key}",
                instrument_id=instrument.id,
                tester_id=owner,
                status=status,
                final_result="PASS" if status != "In Progress" else "PENDING",
                standard_version="workflow-test",
                temperature=temperature,
                humidity=40.0,
                pressure=1013.0,
                laboratory="Initial laboratory",
                location="Initial location",
                remarks="Initial remarks",
            )
            backend.db.session.add(report)
            reports[key] = report
        backend.db.session.commit()
        yield {f"{key}_id": report.id for key, report in reports.items()}


def login(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": "password"})
    assert response.status_code == 200


def _valid_request(client, report_id, mutation):
    url = f"/api/reports/{report_id}/{mutation}"
    if mutation == "environment":
        return client.post(
            url,
            json={
                "temperature": 25.0,
                "humidity": 55.0,
                "pressure": 1000.0,
                "laboratory": "Changed laboratory",
                "location": "Changed location",
                "remarks": "Changed remarks",
            },
        )
    if mutation == "upload":
        return client.post(
            url,
            data={"file": (io.BytesIO(b"valid attachment"), "supporting.pdf")},
            content_type="multipart/form-data",
        )
    if mutation == "evidence":
        return client.post(
            url,
            data={"video": (io.BytesIO(b"valid evidence"), "capture.webm")},
            content_type="multipart/form-data",
        )
    raise AssertionError(f"Unknown mutation: {mutation}")


def _state_snapshot(backend, report_id):
    with backend.app.app_context():
        report = backend.db.session.get(backend.Report, report_id)
        return {
            "environment": (
                report.temperature,
                report.humidity,
                report.pressure,
                report.laboratory,
                report.location,
                report.remarks,
            ),
            "attachments": backend.Attachment.query.filter_by(report_id=report_id).count(),
            "evidence": backend.TestEvidence.query.filter_by(report_id=report_id).count(),
            "upload_files": {path.name for path in Path(backend.UPLOAD).iterdir()},
            "evidence_files": {path.name for path in Path(backend.EVIDENCE).iterdir()},
        }


def _assert_state_unchanged(backend, report_id, before):
    assert _state_snapshot(backend, report_id) == before


@pytest.mark.parametrize("username", ["tester-a", "admin"])
@pytest.mark.parametrize(("report_key", "status"), [("a_review", "Review"), ("a_completed", "Completed")])
@pytest.mark.parametrize("mutation", ["environment", "upload", "evidence"])
def test_review_and_completed_reports_are_locked_for_owner_and_admin(
    workflow_backend, workflow_data, username, report_key, status, mutation
):
    report_id = workflow_data[f"{report_key}_id"]
    before = _state_snapshot(workflow_backend, report_id)
    with workflow_backend.app.test_client() as client:
        login(client, username)
        response = _valid_request(client, report_id, mutation)
    assert response.status_code == 409
    assert response.get_json() == {
        "error": "Report is locked",
        "detail": LOCKED_DETAIL,
        "status": status,
    }
    _assert_state_unchanged(workflow_backend, report_id, before)


def test_owning_tester_can_update_all_supporting_data_while_in_progress(workflow_backend, workflow_data):
    report_id = workflow_data["a_draft_id"]
    with workflow_backend.app.test_client() as client:
        login(client, "tester-a")
        environment = _valid_request(client, report_id, "environment")
        attachment = _valid_request(client, report_id, "upload")
        evidence = _valid_request(client, report_id, "evidence")

    assert environment.status_code == 200
    assert attachment.status_code == 200
    assert evidence.status_code == 200
    with workflow_backend.app.app_context():
        report = workflow_backend.db.session.get(workflow_backend.Report, report_id)
        assert (report.temperature, report.humidity, report.pressure) == (25.0, 55.0, 1000.0)
        attachment_row = workflow_backend.Attachment.query.filter_by(report_id=report_id).one()
        evidence_row = workflow_backend.TestEvidence.query.filter_by(report_id=report_id).one()
        assert (Path(workflow_backend.UPLOAD) / attachment_row.stored_name).is_file()
        assert (Path(workflow_backend.EVIDENCE) / evidence_row.stored_name).is_file()


@pytest.mark.parametrize("filename", ["capture.webm", "capture.mp4", "capture.mov"])
def test_supported_evidence_extensions_are_stored_for_an_owned_draft(
    workflow_backend, workflow_data, filename
):
    report_id = workflow_data["a_draft_id"]
    with workflow_backend.app.test_client() as client:
        login(client, "tester-a")
        response = client.post(
            f"/api/reports/{report_id}/evidence",
            data={"video": (io.BytesIO(b"valid evidence"), filename)},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    with workflow_backend.app.app_context():
        evidence = workflow_backend.TestEvidence.query.filter_by(report_id=report_id).one()
        assert evidence.stored_name.endswith(f".{filename.rsplit('.', 1)[1]}")
        assert (Path(workflow_backend.EVIDENCE) / evidence.stored_name).is_file()


def test_unsupported_evidence_extension_creates_no_row_or_file(
    workflow_backend, workflow_data
):
    report_id = workflow_data["a_draft_id"]
    before = _state_snapshot(workflow_backend, report_id)
    with workflow_backend.app.test_client() as client:
        login(client, "tester-a")
        response = client.post(
            f"/api/reports/{report_id}/evidence",
            data={"video": (io.BytesIO(b"invalid evidence"), "capture.exe")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Video type not allowed"}
    _assert_state_unchanged(workflow_backend, report_id, before)


def test_evidence_workflow_lock_precedes_extension_validation(
    workflow_backend, workflow_data
):
    report_id = workflow_data["a_review_id"]
    before = _state_snapshot(workflow_backend, report_id)
    with workflow_backend.app.test_client() as client:
        login(client, "tester-a")
        response = client.post(
            f"/api/reports/{report_id}/evidence",
            data={"video": (io.BytesIO(b"invalid evidence"), "capture.exe")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "Report is locked",
        "detail": LOCKED_DETAIL,
        "status": "Review",
    }
    _assert_state_unchanged(workflow_backend, report_id, before)


@pytest.mark.parametrize("mutation", ["environment", "upload", "evidence"])
def test_cross_owner_tester_is_denied_before_lock_or_payload_validation(
    workflow_backend, workflow_data, mutation
):
    report_id = workflow_data["b_review_id"]
    before = _state_snapshot(workflow_backend, report_id)
    with workflow_backend.app.test_client() as client:
        login(client, "tester-a")
        url = f"/api/reports/{report_id}/{mutation}"
        if mutation == "environment":
            response = client.post(url, data=b"{", content_type="application/json")
        elif mutation == "evidence":
            response = client.post(
                url,
                data={"video": (io.BytesIO(b"invalid evidence"), "capture.exe")},
                content_type="multipart/form-data",
            )
        else:
            response = client.post(url, data={}, content_type="multipart/form-data")
    assert response.status_code == 403
    _assert_state_unchanged(workflow_backend, report_id, before)


def test_reviewer_and_manufacturer_mutations_remain_denied_and_reviewer_can_approve(
    workflow_backend, workflow_data
):
    report_id = workflow_data["a_review_id"]
    with workflow_backend.app.test_client() as client:
        for username in ("reviewer", "manufacturer"):
            login(client, username)
            for mutation in ("environment", "upload", "evidence"):
                assert _valid_request(client, report_id, mutation).status_code == 403
        login(client, "manufacturer")
        assert client.post(f"/api/reports/{report_id}/approve").status_code == 403
        login(client, "reviewer")
        approved = client.post(f"/api/reports/{report_id}/approve")
    assert approved.status_code == 200
    assert approved.get_json()["status"] == "Completed"
