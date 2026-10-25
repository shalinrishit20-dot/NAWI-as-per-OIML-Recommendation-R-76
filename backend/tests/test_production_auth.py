"""Production authentication configuration tests for the real application module.

Each test imports app.py against an isolated SQLite database.  The module is
executed directly from its source path and is deliberately never registered in
sys.modules, so this suite neither stubs nor replaces the application or rules
packages used by other tests.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import quote

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = BACKEND_ROOT / "app.py"
TEST_SECRET = "production-auth-deterministic-test-secret"
DEMO_USERS = (
    ("admin", "admin123", "Admin"),
    ("tester", "tester123", "Tester"),
    ("reviewer", "reviewer123", "Reviewer"),
    ("manufacturer", "manufacturer123", "Manufacturer"),
)


def _sqlite_url(database_path: Path) -> str:
    return f"sqlite:///{quote(database_path.resolve().as_posix(), safe='/:')}"


@pytest.fixture()
def load_backend(tmp_path):
    """Load an unregistered real app module with temporary explicit settings."""
    loaded_modules = []

    def load(
        *,
        secret: str | None,
        demo_mode: str | None,
        secure_cookie: str | None = "0",
        data_dir: str | None = None,
        database_name: str = "auth.sqlite",
        database_url: str | None = None,
    ):
        database_url = database_url or _sqlite_url(tmp_path / database_name)
        keys = (
            "DATABASE_URL",
            "SECRET_KEY",
            "NAWI_DEMO_MODE",
            "NAWI_SESSION_COOKIE_SECURE",
            "NAWI_DATA_DIR",
        )
        previous = {key: os.environ.get(key) for key in keys}
        present = {key: key in os.environ for key in keys}
        previous_sys_path = list(sys.path)

        values = {
            "DATABASE_URL": database_url,
            "SECRET_KEY": secret,
            "NAWI_DEMO_MODE": demo_mode,
            "NAWI_SESSION_COOKIE_SECURE": secure_cookie,
            "NAWI_DATA_DIR": data_dir,
        }
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if str(BACKEND_ROOT) not in sys.path:
            sys.path.insert(0, str(BACKEND_ROOT))

        spec = importlib.util.spec_from_file_location("production_auth_app", APP_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = previous_sys_path
            for key in keys:
                if present[key]:
                    os.environ[key] = previous[key]  # type: ignore[arg-type]
                else:
                    os.environ.pop(key, None)

        loaded_modules.append(module)
        return module

    yield load

    for module in loaded_modules:
        with module.app.app_context():
            module.db.session.remove()
            module.db.engine.dispose()


@pytest.mark.parametrize("secret", [None, "", " \t\n "])
def test_missing_or_blank_secret_key_fails_startup(load_backend, secret):
    with pytest.raises(RuntimeError, match="SECRET_KEY must be set to a non-empty value"):
        load_backend(secret=secret, demo_mode=None)


def test_legacy_repository_secret_fails_startup(load_backend):
    with pytest.raises(RuntimeError, match="SECRET_KEY must not use the known demo secret value"):
        load_backend(
            secret="nawi-testpro-demo-secret-change-in-production",
            demo_mode=None,
        )


def test_valid_supplied_secret_starts_normally(load_backend):
    backend = load_backend(secret=TEST_SECRET, demo_mode=None, secure_cookie=None)

    assert backend.app.config["SECRET_KEY"] == TEST_SECRET
    assert backend.app.config["DEMO_MODE"] is False
    assert backend.app.config["SESSION_COOKIE_SECURE"] is True
    assert backend.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert backend.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_default_data_root_keeps_current_local_paths(load_backend):
    backend = load_backend(secret=TEST_SECRET, demo_mode=None)

    assert backend.DATA_DIR == backend.BASE
    assert backend.UPLOAD == os.path.join(backend.BASE, "uploads")
    assert backend.REPORTS == os.path.join(backend.BASE, "reports")
    assert backend.PRODUCT_IMAGES == os.path.join(backend.BASE, "uploads", "products")
    assert backend.EVIDENCE == os.path.join(backend.BASE, "uploads", "evidence")
    assert backend.FRONTEND_DIST == os.path.join(backend.BASE, "frontend", "dist")


def test_custom_data_root_moves_only_mutable_runtime_paths(load_backend, tmp_path):
    data_root = tmp_path / "persistent-data"
    explicit_database_url = _sqlite_url(tmp_path / "separate-database.sqlite")
    backend = load_backend(
        secret=TEST_SECRET,
        demo_mode=None,
        data_dir=str(data_root),
        database_url=explicit_database_url,
    )

    assert backend.DATA_DIR == str(data_root)
    assert backend.UPLOAD == str(data_root / "uploads")
    assert backend.REPORTS == str(data_root / "reports")
    assert backend.PRODUCT_IMAGES == str(data_root / "uploads" / "products")
    assert backend.EVIDENCE == str(data_root / "uploads" / "evidence")
    assert backend.app.config["SQLALCHEMY_DATABASE_URI"] == explicit_database_url
    assert backend.FRONTEND_DIST == os.path.join(backend.BASE, "frontend", "dist")
    for directory in (backend.UPLOAD, backend.REPORTS, backend.PRODUCT_IMAGES, backend.EVIDENCE):
        assert Path(directory).is_dir()


@pytest.mark.parametrize("role", ["Admin", "Tester", "Reviewer", "Manufacturer"])
def test_create_user_cli_creates_each_valid_role_with_a_hashed_password(load_backend, role):
    backend = load_backend(secret=TEST_SECRET, demo_mode="0")
    username = f"{role.lower()}-operator"
    runner = backend.app.test_cli_runner()

    result = runner.invoke(
        args=["create-user", "--username", username, "--role", role],
        input="test-password\ntest-password\n",
    )

    assert result.exit_code == 0, result.output
    assert f"Created {role} user '{username}'." in result.output
    with backend.app.app_context():
        user = backend.User.query.filter_by(username=username).one()
        assert user.role == role
        assert backend.check_password_hash(user.password_hash, "test-password")
        assert not backend.check_password_hash(user.password_hash, "another-password")


def test_create_user_cli_refuses_existing_username_without_overwriting_password(load_backend):
    backend = load_backend(secret=TEST_SECRET, demo_mode="0")
    runner = backend.app.test_cli_runner()

    first = runner.invoke(
        args=["create-user", "--username", "operator", "--role", "Admin"],
        input="original-password\noriginal-password\n",
    )
    assert first.exit_code == 0, first.output
    with backend.app.app_context():
        original_hash = backend.User.query.filter_by(username="operator").one().password_hash

    duplicate = runner.invoke(
        args=["create-user", "--username", "operator", "--role", "Tester"],
        input="replacement-password\nreplacement-password\n",
    )
    assert duplicate.exit_code != 0
    assert "already exists" in duplicate.output
    with backend.app.app_context():
        user = backend.User.query.filter_by(username="operator").one()
        assert user.role == "Admin"
        assert user.password_hash == original_hash
        assert backend.check_password_hash(user.password_hash, "original-password")
        assert not backend.check_password_hash(user.password_hash, "replacement-password")


@pytest.mark.parametrize(
    ("secure_cookie", "expected"),
    [
        (None, True),
        ("", True),
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("unexpected", True),
        ("0", False),
        ("FALSE", False),
        ("No", False),
        ("off", False),
    ],
)
def test_session_cookie_secure_configuration_parses_explicit_false_values(
    load_backend, secure_cookie, expected
):
    backend = load_backend(
        secret=TEST_SECRET,
        demo_mode=None,
        secure_cookie=secure_cookie,
        database_name=f"cookie-{secure_cookie or 'unset'}.sqlite",
    )
    assert backend.app.config["SESSION_COOKIE_SECURE"] is expected
    assert backend.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert backend.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_login_cookie_attributes_follow_secure_cookie_configuration(load_backend):
    production = load_backend(
        secret=TEST_SECRET,
        demo_mode="1",
        secure_cookie=None,
        database_name="production-cookie.sqlite",
    )
    with production.app.test_client() as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
    assert response.status_code == 200
    production_cookie = response.headers["Set-Cookie"]
    assert "; Secure" in production_cookie
    assert "; HttpOnly" in production_cookie
    assert "SameSite=Lax" in production_cookie

    local = load_backend(
        secret=TEST_SECRET,
        demo_mode="1",
        secure_cookie="0",
        database_name="local-cookie.sqlite",
    )
    with local.app.test_client() as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
    assert response.status_code == 200
    local_cookie = response.headers["Set-Cookie"]
    assert "; Secure" not in local_cookie
    assert "; HttpOnly" in local_cookie
    assert "SameSite=Lax" in local_cookie


@pytest.mark.parametrize("demo_mode", [None, "0", "false"])
def test_demo_mode_off_does_not_seed_users_and_reports_mode(load_backend, demo_mode):
    backend = load_backend(secret=TEST_SECRET, demo_mode=demo_mode)

    with backend.app.app_context():
        assert backend.User.query.count() == 0

    with backend.app.test_client() as client:
        anonymous = client.get("/api/auth/me")
        assert anonymous.status_code == 200
        assert anonymous.get_json() == {
            "authenticated": False,
            "user": None,
            "demo_mode": False,
        }

        denied = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert denied.status_code == 401


@pytest.mark.parametrize("demo_mode", ["1", "TrUe", "yes", "ON"])
def test_explicit_truthy_demo_modes_seed_expected_accounts(load_backend, demo_mode):
    backend = load_backend(
        secret=TEST_SECRET,
        demo_mode=demo_mode,
        database_name=f"demo-{demo_mode.lower()}.sqlite",
    )

    with backend.app.app_context():
        users = {user.username: user.role for user in backend.User.query.all()}
        assert users == {username: role for username, _password, role in DEMO_USERS}

    with backend.app.test_client() as client:
        anonymous = client.get("/api/auth/me")
        assert anonymous.get_json() == {
            "authenticated": False,
            "user": None,
            "demo_mode": True,
        }

        for username, password, role in DEMO_USERS:
            response = client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
            assert response.status_code == 200
            assert response.get_json()["user"]["role"] == role

            authenticated = client.get("/api/auth/me")
            assert authenticated.get_json()["authenticated"] is True
            assert authenticated.get_json()["demo_mode"] is True
            assert authenticated.get_json()["user"]["username"] == username

            assert client.post("/api/auth/logout").status_code == 200


def test_demo_seed_does_not_overwrite_an_existing_username(load_backend):
    initial = load_backend(
        secret=TEST_SECRET,
        demo_mode=None,
        database_name="existing-user.sqlite",
    )
    with initial.app.app_context():
        initial.db.session.add(
            initial.User(
                username="admin",
                role="Admin",
                password_hash=initial.generate_password_hash("custom-password"),
            )
        )
        initial.db.session.commit()
        initial.db.session.remove()
        initial.db.engine.dispose()

    demo = load_backend(
        secret=TEST_SECRET,
        demo_mode="on",
        database_name="existing-user.sqlite",
    )
    with demo.app.app_context():
        admin = demo.User.query.filter_by(username="admin").one()
        assert demo.check_password_hash(admin.password_hash, "custom-password")
        assert not demo.check_password_hash(admin.password_hash, "admin123")
        assert demo.User.query.count() == 4

    with demo.app.test_client() as client:
        known_demo_password = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert known_demo_password.status_code == 401

        retained_password = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "custom-password"},
        )
        assert retained_password.status_code == 200
