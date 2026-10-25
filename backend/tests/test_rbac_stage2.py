import importlib.util
import io
import os
import sys
from pathlib import Path
from urllib.parse import quote

import pytest


# app.py configures SQLAlchemy and creates tables at import time. Load the real
# module only inside this fixture, after pointing DATABASE_URL at pytest storage.
def _backend_root() -> Path:
    for directory in Path(__file__).resolve().parents:
        if (directory / "app.py").is_file():
            return directory
    raise RuntimeError("Could not find the backend app.py for the Stage 2 ownership tests")


BACKEND_ROOT = _backend_root()
APP_PATH = BACKEND_ROOT / "app.py"


def _sqlite_url(database_path: Path) -> str:
    return f"sqlite:///{quote(database_path.resolve().as_posix(), safe='/:')}"


@pytest.fixture(scope="session")
def ownership_backend(tmp_path_factory):
    database_path = tmp_path_factory.mktemp("stage2_report_ownership_db") / "ownership.sqlite"
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
    os.environ["SECRET_KEY"] = "stage2-rbac-test-secret"
    os.environ["NAWI_DEMO_MODE"] = "0"
    os.environ["NAWI_SESSION_COOKIE_SECURE"] = "0"
    os.environ["NAWI_DATA_DIR"] = str(database_path.parent)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    spec = importlib.util.spec_from_file_location("app", APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        # This imports the project's real rules package; no rule modules are
        # stubbed or replaced by this test.
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

    storage_dir = tmp_path_factory.mktemp("stage2_report_ownership_storage")
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
def ownership_data(ownership_backend):
    backend = ownership_backend
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
            model="Ownership scale",
            serial_number="OWNERSHIP-001",
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
        fixtures = (
            ("a_draft", "TESTER-A-DRAFT", users["tester-a"].id, "In Progress", "PENDING"),
            ("a_review", "TESTER-A-REVIEW", users["tester-a"].id, "Review", "PASS"),
            ("b_draft", "TESTER-B-DRAFT", users["tester-b"].id, "In Progress", "PENDING"),
            ("b_review", "TESTER-B-REVIEW", users["tester-b"].id, "Review", "PASS"),
            ("b_completed", "TESTER-B-COMPLETED", users["tester-b"].id, "Completed", "PASS"),
            ("unowned", "UNOWNED-REVIEW", None, "Review", "PASS"),
        )
        for key, number, tester_id, status, final_result in fixtures:
            report = backend.Report(
                report_number=number,
                instrument_id=instrument.id,
                tester_id=tester_id,
                status=status,
                final_result=final_result,
                standard_version="ownership-test",
            )
            backend.db.session.add(report)
            reports[key] = report
        backend.db.session.commit()

        yield {
            "instrument_id": instrument.id,
            "tester_a_id": users["tester-a"].id,
            "tester_b_id": users["tester-b"].id,
            **{f"{key}_id": report.id for key, report in reports.items()},
        }


def login(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": "password"})
    assert response.status_code == 200


def test_tester_list_and_dashboard_are_scoped_to_owner(ownership_backend, ownership_data):
    with ownership_backend.app.test_client() as client:
        login(client, "tester-a")
        reports = client.get("/api/reports")
        assert reports.status_code == 200
        assert {row["id"] for row in reports.get_json()} == {
            ownership_data["a_draft_id"],
            ownership_data["a_review_id"],
        }
        assert client.get("/api/reports?q=TESTER-B").get_json() == []

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        body = dashboard.get_json()
        assert body["stats"] == {
            "instruments": 1,
            "reports": 2,
            "in_progress": 1,
            "review": 1,
            "completed": 0,
            "passed": 1,
            "failed": 0,
        }
        assert {row["id"] for row in body["recent"]} == {
            ownership_data["a_draft_id"],
            ownership_data["a_review_id"],
        }


def test_tester_own_detail_and_exports_work_but_cross_owner_reads_are_forbidden(ownership_backend, ownership_data):
    with ownership_backend.app.test_client() as client:
        login(client, "tester-a")
        own_id = ownership_data["a_draft_id"]
        other_id = ownership_data["b_draft_id"]
        assert client.get(f"/api/reports/{own_id}").status_code == 200
        assert client.get(f"/api/reports/{own_id}/pdf").status_code == 200
        assert client.get(f"/api/reports/{own_id}/word").status_code == 200
        assert client.get(f"/api/reports/{other_id}").status_code == 403
        assert client.get(f"/api/reports/{other_id}/pdf").status_code == 403
        assert client.get(f"/api/reports/{other_id}/word").status_code == 403


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("post", "observations", {"not": "a valid observation"}),
        ("put", "repeatability/not-a-series", {}),
        ("put", "eccentricity", {}),
        ("put", "zero-setting", {}),
        ("put", "tare-weighing", {}),
        ("post", "environment", {}),
        ("post", "complete", {}),
        ("post", "upload", {}),
        ("post", "evidence", {}),
    ],
)
def test_tester_cross_owner_mutations_are_forbidden_before_workflow_or_payload_validation(
    ownership_backend, ownership_data, method, suffix, payload
):
    with ownership_backend.app.test_client() as client:
        login(client, "tester-a")
        response = client.open(
            f"/api/reports/{ownership_data['b_review_id']}/{suffix}",
            method=method.upper(),
            json=payload,
        )
        assert response.status_code == 403


def test_tester_media_access_uses_linked_report_ownership(ownership_backend, ownership_data):
    backend = ownership_backend
    evidence_name = "opaque-evidence-token.webm"
    attachment_name = "opaque-attachment-token.txt"
    evidence_path = Path(backend.EVIDENCE) / evidence_name
    attachment_path = Path(backend.UPLOAD) / attachment_name
    with backend.app.app_context():
        backend.db.session.add_all([
            backend.TestEvidence(
                report_id=ownership_data["b_draft_id"],
                filename="session.webm",
                stored_name=evidence_name,
                sha256="evidence-hash",
            ),
            backend.Attachment(
                report_id=ownership_data["b_draft_id"],
                filename="notes.txt",
                stored_name=attachment_name,
            ),
        ])
        backend.db.session.commit()
    evidence_path.write_bytes(b"test evidence")
    attachment_path.write_bytes(b"test attachment")
    try:
        with backend.app.test_client() as client:
            login(client, "tester-a")
            assert client.get(f"/media/evidence/{evidence_name}").status_code == 403
            assert client.get(f"/media/uploads/{attachment_name}").status_code == 403
            login(client, "tester-b")
            assert client.get(f"/media/evidence/{evidence_name}").status_code == 200
            assert client.get(f"/media/uploads/{attachment_name}").status_code == 200
    finally:
        evidence_path.unlink(missing_ok=True)
        attachment_path.unlink(missing_ok=True)


def test_tester_can_create_and_submit_own_report(ownership_backend, ownership_data):
    with ownership_backend.app.test_client() as client:
        login(client, "tester-a")
        created = client.post("/api/reports", json={"instrument_id": ownership_data["instrument_id"]})
        assert created.status_code == 201
        report_id = created.get_json()["id"]

        with ownership_backend.app.app_context():
            report = ownership_backend.db.session.get(ownership_backend.Report, report_id)
            assert report.tester_id == ownership_data["tester_a_id"]

        assert client.post(
            f"/api/reports/{report_id}/observations",
            json={"applied_load": 5000, "reference_value": 5000, "indication": 5000.5, "zero_error": 0.2},
        ).status_code == 201
        assert client.put(
            f"/api/reports/{report_id}/repeatability/half_max",
            json={"applied_load": 15000, "readings": [15000] * 10},
        ).status_code == 200
        assert client.put(
            f"/api/reports/{report_id}/repeatability/near_max",
            json={"applied_load": 30000, "readings": [30000] * 10},
        ).status_code == 200
        assert client.put(
            f"/api/reports/{report_id}/eccentricity",
            json={"position_errors": {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}},
        ).status_code == 200
        assert client.put(
            f"/api/reports/{report_id}/zero-setting",
            json={"setting_mode": "non_automatic", "indication": 0},
        ).status_code == 200
        assert client.put(
            f"/api/reports/{report_id}/tare-weighing",
            json={
                "tare_value": 0,
                "observations": [
                    {"net_load": 5000, "reference_value": 5000, "indication": 5000.5, "zero_error": 0.2}
                    for _ in range(5)
                ],
            },
        ).status_code == 200
        submitted = client.post(f"/api/reports/{report_id}/complete")
        assert submitted.status_code == 200
        assert submitted.get_json()["status"] == "Review"


def test_admin_retains_cross_owner_access(ownership_backend, ownership_data):
    with ownership_backend.app.test_client() as client:
        login(client, "admin")
        report_id = ownership_data["b_draft_id"]
        assert client.get(f"/api/reports/{report_id}").status_code == 200
        assert client.get(f"/api/reports/{report_id}/pdf").status_code == 200
        assert client.get(f"/api/reports/{report_id}/word").status_code == 200
        assert client.post(
            f"/api/reports/{report_id}/environment",
            json={"temperature": 20, "humidity": 50, "pressure": 1013},
        ).status_code == 200


def test_reviewer_behavior_is_status_based_not_tester_based(ownership_backend, ownership_data):
    with ownership_backend.app.test_client() as client:
        login(client, "reviewer")
        assert client.get(f"/api/reports/{ownership_data['b_draft_id']}").status_code == 403
        assert client.get(f"/api/reports/{ownership_data['b_review_id']}").status_code == 200
        assert client.get(f"/api/reports/{ownership_data['b_completed_id']}").status_code == 200
        approved = client.post(f"/api/reports/{ownership_data['b_review_id']}/approve")
        assert approved.status_code == 200
        assert approved.get_json()["status"] == "Completed"


def test_tester_is_denied_unowned_report(ownership_backend, ownership_data):
    with ownership_backend.app.test_client() as client:
        login(client, "tester-a")
        assert client.get(f"/api/reports/{ownership_data['unowned_id']}").status_code == 403
        assert client.get("/api/reports?q=UNOWNED-REVIEW").get_json() == []
