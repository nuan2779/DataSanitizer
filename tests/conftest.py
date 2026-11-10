import pytest
from fastapi.testclient import TestClient
from backend.main import app
import backend.database as db_module

@pytest.fixture
def isolated_client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_datasanitizer.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db_module.init_db()
    with TestClient(app) as client:
        yield client
