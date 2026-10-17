import pytest
from app import db

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Isolate all database operations during test runs using an ephemeral SQLite database.

    Guarantees no test reads or writes to the local development database file (aftermath.db).
    """
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setenv("AFTERMATH_DB_PATH", test_db)
    db.init_db(seed=True)
    yield
