import base64
import importlib.util
import io
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import pytest


# This test is deliberately self-contained: app.py reads DATABASE_URL and calls
# db.create_all() while it is imported.  The temporary database must therefore
# be configured before executing the application module, not in a per-test
# fixture after the import has already happened.
def _backend_root() -> Path:
    for directory in Path(__file__).resolve().parents:
        if (directory / "app.py").is_file():
            return directory
    raise RuntimeError("Could not find the backend app.py for the Stage 1 RBAC tests")


BACKEND_ROOT = _backend_root()
APP_PATH = BACKEND_ROOT / "app.py"


def _sqlite_url(database_path: Path) -> str:
    """Return a SQLAlchemy SQLite URL valid for POSIX and Windows paths."""
    # On POSIX this produces sqlite:////tmp/...; on Windows it produces
    # sqlite:///C:/... .  Keeping '/' and ':' unescaped is required for the
    # SQLite path component, while quoting the rest protects unusual temp paths.
    path = quote(database_path.resolve().as_posix(), safe="/:")
    return f"sqlite:///{path}"


@pytest.fixture(scope="session")
def backend(tmp_path_factory):
    """Load the real application against a database owned by this test session."""
    database_dir = tmp_path_factory.mktemp("stage1_rbac_database")
    database_path = database_dir / "nawi_rbac.sqlite"
    database_url = _sqlite_url(database_path)

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

    # Do not import or replace rules/rules.* here.  app.py imports the project's
    # actual OIML package while its own directory is temporarily on sys.path.
    os.environ["DATABASE_URL"] = database_url
    os.environ["SECRET_KEY"] = "stage1-rbac-test-secret"
    os.environ["NAWI_DEMO_MODE"] = "0"
    os.environ["NAWI_SESSION_COOKIE_SECURE"] = "0"
    os.environ["NAWI_DATA_DIR"] = str(database_dir)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    # Execute a second, unregistered copy of the real app module.  The module is
    # intentionally never added to sys.modules, so this test cannot replace an
    # app or rules module that another test has already imported.
    spec = importlib.util.spec_from_file_location("app", APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        # The application has already captured its database URI.  Restoring the
        # process environment prevents this harness affecting other test modules.
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

    try:
        module.app.config.update(TESTING=True)
        # Route functions resolve these module globals at request time.  Point
        # the dynamically loaded test app at pytest-owned storage too, so image
        # and media assertions cannot leave files in the real backend/uploads.
        storage_dir = tmp_path_factory.mktemp("stage1_rbac_storage")
        module.UPLOAD = str(storage_dir / "uploads")
        module.REPORTS = str(storage_dir / "reports")
        module.PRODUCT_IMAGES = str(storage_dir / "uploads" / "products")
        module.EVIDENCE = str(storage_dir / "uploads" / "evidence")
        for directory in (module.UPLOAD, module.REPORTS, module.PRODUCT_IMAGES, module.EVIDENCE):
            Path(directory).mkdir(parents=True, exist_ok=True)
        yield module
    finally:
        with module.app.app_context():
            module.db.session.remove()
            module.db.drop_all()
            module.db.engine.dispose()
        # tempfile/pytest owns the parent; explicitly removing this file makes
        # it clear that no database under backend/instance is touched.
        database_path.unlink(missing_ok=True)


@pytest.fixture()
def seeded(backend):
    with backend.app.app_context():
        backend.db.session.remove()
        backend.db.drop_all()
        backend.db.create_all()
        users = {}
        for username, role in (
            ("admin", "Admin"),
            ("tester", "Tester"),
            ("reviewer", "Reviewer"),
            ("manufacturer", "Manufacturer"),
        ):
            user = backend.User(
                username=username,
                role=role,
                password_hash=backend.generate_password_hash("password"),
            )
            backend.db.session.add(user)
            users[role] = user
        backend.db.session.flush()
        instrument = backend.Instrument(
            manufacturer="NAWI",
            model="Test scale",
            serial_number="RBAC-001",
            accuracy_class="III",
            max_capacity=30,
            min_capacity=0.2,
            e=0.01,
            d=0.01,
            unit="kg",
        )
        backend.db.session.add(instrument)
        backend.db.session.flush()
        reports = {}
        for suffix, status in (("draft", "In Progress"), ("review", "Review"), ("completed", "Completed")):
            report = backend.Report(
                report_number=f"RBAC-{suffix}",
                instrument_id=instrument.id,
                tester_id=users["Tester"].id,
                status=status,
                final_result="PASS" if status != "In Progress" else "PENDING",
                standard_version="rbac-test",
            )
            backend.db.session.add(report)
            reports[status] = report
        backend.db.session.commit()
        yield {
            "instrument_id": instrument.id,
            "draft_id": reports["In Progress"].id,
            "review_id": reports["Review"].id,
            "completed_id": reports["Completed"].id,
        }


def login(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": "password"})
    assert response.status_code == 200


def image_upload():
    # 1x1 transparent PNG; valid input for the existing PIL perceptual-hash path.
    image = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLJzQAAAABJRU5ErkJggg==")
    return {"images": (io.BytesIO(image), "product.png")}


def test_tester_cannot_approve(backend, seeded):
    with backend.app.test_client() as client:
        login(client, "tester")
        assert client.post(f"/api/reports/{seeded['review_id']}/approve").status_code == 403


def test_reviewer_write_endpoints_are_forbidden(backend, seeded):
    with backend.app.test_client() as client:
        login(client, "reviewer")
        draft = seeded["draft_id"]
        blocked = [
            ("post", "/api/reports", {"instrument_id": seeded["instrument_id"]}),
            ("post", f"/api/reports/{draft}/observations", {"applied_load": 1, "reference_value": 1, "indication": 1, "zero_error": 0}),
            ("put", f"/api/reports/{draft}/zero-setting", {"indication": 0}),
            ("put", f"/api/reports/{draft}/repeatability/half_max", {"applied_load": 1, "readings": [1, 1, 1]}),
            ("put", f"/api/reports/{draft}/eccentricity", {"position_errors": {"Q1": 0}}),
            ("put", f"/api/reports/{draft}/tare-weighing", {"tare_value": 0, "observations": []}),
            ("post", f"/api/reports/{draft}/environment", {"temperature": 20}),
            ("post", f"/api/reports/{draft}/evidence", {}),
            ("post", f"/api/reports/{draft}/upload", {}),
            ("post", f"/api/reports/{draft}/complete", {}),
        ]
        for method, url, payload in blocked:
            assert client.open(url, method=method.upper(), json=payload).status_code == 403, url


def test_reviewer_reads_only_review_and_completed_and_can_approve(backend, seeded):
    with backend.app.test_client() as client:
        login(client, "reviewer")
        listing = client.get("/api/reports")
        assert listing.status_code == 200
        assert {row["status"] for row in listing.get_json()} == {"Review", "Completed"}
        assert client.get(f"/api/reports/{seeded['review_id']}").status_code == 200
        assert client.get(f"/api/reports/{seeded['completed_id']}").status_code == 200
        assert client.get(f"/api/reports/{seeded['draft_id']}").status_code == 403
        assert client.post(f"/api/reports/{seeded['review_id']}/approve").status_code == 200


def test_manufacturer_cannot_access_internal_reports_or_write_technical_data(backend, seeded):
    with backend.app.test_client() as client:
        login(client, "manufacturer")
        draft = seeded["draft_id"]
        for url in (
            "/api/reports",
            f"/api/reports/{draft}",
            f"/api/reports/{draft}/pdf",
            f"/api/reports/{draft}/word",
            "/media/evidence/not-a-real-file",
            "/media/uploads/not-a-real-file",
        ):
            assert client.get(url).status_code == 403, url
        assert client.post("/api/reports", json={"instrument_id": seeded["instrument_id"]}).status_code == 403
        assert client.post(
            f"/api/reports/{draft}/observations",
            json={"applied_load": 1, "reference_value": 1, "indication": 1, "zero_error": 0},
        ).status_code == 403


def test_manufacturer_dashboard_keeps_aggregates_but_hides_recent_reports(backend, seeded):
    with backend.app.test_client() as client:
        login(client, "manufacturer")
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["stats"]["instruments"] == 1
        assert payload["stats"]["reports"] == 3
        assert payload["recent"] == []


def test_manufacturer_can_upload_product_images_but_tester_cannot(backend, seeded):
    url = f"/api/instruments/{seeded['instrument_id']}/images"
    created_files = []
    try:
        with backend.app.test_client() as manufacturer:
            login(manufacturer, "manufacturer")
            response = manufacturer.post(url, data=image_upload(), content_type="multipart/form-data")
            assert response.status_code == 200
            created_files = [Path(backend.PRODUCT_IMAGES) / Path(image_url).name for image_url in response.get_json()["images"]]
        with backend.app.test_client() as tester:
            login(tester, "tester")
            assert tester.post(url, data=image_upload(), content_type="multipart/form-data").status_code == 403
    finally:
        for path in created_files:
            path.unlink(missing_ok=True)


def test_reviewer_media_status_checks_use_evidence_and_attachment_relations(backend, seeded):
    draft_evidence = "rbac-draft-evidence.webm"
    review_evidence = "rbac-review-evidence.webm"
    draft_attachment = "rbac-draft-attachment.txt"
    review_attachment = "rbac-review-attachment.txt"
    paths = [
        Path(backend.EVIDENCE) / draft_evidence,
        Path(backend.EVIDENCE) / review_evidence,
        Path(backend.UPLOAD) / draft_attachment,
        Path(backend.UPLOAD) / review_attachment,
    ]
    with backend.app.app_context():
        backend.db.session.add_all([
            backend.TestEvidence(report_id=seeded["draft_id"], filename="draft.webm", stored_name=draft_evidence, sha256="a"),
            backend.TestEvidence(report_id=seeded["review_id"], filename="review.webm", stored_name=review_evidence, sha256="b"),
            backend.Attachment(report_id=seeded["draft_id"], filename="draft.txt", stored_name=draft_attachment),
            backend.Attachment(report_id=seeded["review_id"], filename="review.txt", stored_name=review_attachment),
        ])
        backend.db.session.commit()
    for path in paths:
        path.write_bytes(b"RBAC test content")
    try:
        with backend.app.test_client() as client:
            login(client, "reviewer")
            assert client.get(f"/media/evidence/{draft_evidence}").status_code == 403
            assert client.get(f"/media/uploads/{draft_attachment}").status_code == 403
            assert client.get(f"/media/evidence/{review_evidence}").status_code == 200
            assert client.get(f"/media/uploads/{review_attachment}").status_code == 200
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


@pytest.mark.parametrize("username", ["tester", "reviewer", "manufacturer"])
def test_non_admin_cannot_access_audit(backend, username, seeded):
    with backend.app.test_client() as client:
        login(client, username)
        assert client.get("/api/audit").status_code == 403


def test_admin_retains_stage_one_capabilities(backend, seeded):
    with backend.app.test_client() as client:
        login(client, "admin")
        assert client.get("/api/dashboard").status_code == 200
        assert client.post("/api/instruments", json={
            "manufacturer": "NAWI", "model": "Admin scale", "serial_number": "RBAC-ADMIN-001",
            "accuracy_class": "III", "min_capacity": 0.2, "max_capacity": 30, "e": 0.01, "d": 0.01, "unit": "kg",
        }).status_code == 201
        assert client.post("/api/reports", json={"instrument_id": seeded["instrument_id"]}).status_code == 201
        assert client.put(f"/api/reports/{seeded['draft_id']}/zero-setting", json={"setting_mode": "non_automatic", "indication": 0, "additional_load": 0.005}).status_code == 200
        assert client.post(f"/api/reports/{seeded['draft_id']}/environment", json={"temperature": 20, "humidity": 50, "pressure": 1013}).status_code == 200
        assert client.post(f"/api/reports/{seeded['review_id']}/approve").status_code == 200
        assert client.get("/api/audit").status_code == 200
