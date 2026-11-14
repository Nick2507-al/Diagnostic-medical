"""Test harness: dedicated Postgres database, migrated with Alembic, fake AI provider."""
import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def _read_env() -> dict[str, str]:
    values = {}
    env_file = BACKEND / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


_env = _read_env()
TEST_DB = os.environ.get("TEST_DATABASE_URL") or _env.get("TEST_DATABASE_URL")
if not TEST_DB or "mediai_test" not in TEST_DB:
    raise RuntimeError("TEST_DATABASE_URL must point to the mediai_test database")

# Must be set before the app (and its settings/engine) is imported.
os.environ.update({
    "DATABASE_URL": TEST_DB,
    "MEDIAI_DATABASE_URL": TEST_DB,
    "ENVIRONMENT": "test",
    "ANTHROPIC_API_KEY": "",
    "DEFAULT_USER_EMAIL": "seed@example.com",
    "DEFAULT_USER_PASSWORD": "SeedPassw0rd!",
})

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ratelimit import limiter  # noqa: E402
from app.services import ai as ai_module  # noqa: E402

from .fakes import FakeAI  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_state():
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE chat_messages, conversations, analysis_files, analyses, user_sessions, users CASCADE"
        ))
    limiter.reset()
    yield


@pytest.fixture
def fake_ai():
    fake = FakeAI()
    app.dependency_overrides[ai_module.get_ai] = lambda: fake
    yield fake
    app.dependency_overrides.pop(ai_module.get_ai, None)


def _client() -> TestClient:
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def client(fake_ai):
    with _client() as c:
        yield c


@pytest.fixture
def make_user(fake_ai):
    """Factory returning a logged-in client for a fresh account."""
    clients = []

    def _make(email="doc@example.com", password="Passw0rdSolide", name="Dr Test"):
        c = _client().__enter__()
        clients.append(c)
        r = c.post("/api/auth/register", json={"email": email, "password": password, "full_name": name})
        assert r.status_code == 201, r.text
        c.headers["X-CSRF-Token"] = c.cookies.get("mediai_csrf")
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
