import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.main import app


@pytest.fixture
def isolated_client(tmp_path, monkeypatch):
    """Run API tests against a fresh SQLite file instead of the real workspace DB."""
    db_path = tmp_path / "datasanitizer-test.db"
    monkeypatch.setattr(database, "DB_DIR", str(tmp_path))
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    database.init_db()

    with TestClient(app) as client:
        yield client
