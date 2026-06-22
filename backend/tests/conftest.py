import os
import tempfile

import pytest

temp_dir = tempfile.mkdtemp(prefix="speechflow_test_")
os.environ["TEMP_DIR"] = temp_dir
os.environ["UPLOAD_DIR"] = temp_dir
os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir}/test.db"
os.environ["SECRET_KEY"] = "test-only-key"
os.environ["ADMIN_PASSWORD"] = "test-password"

from backend.app import create_app
from backend.app.db import Base, engine, SessionLocal


@pytest.fixture
def app():
    Base.metadata.create_all(bind=engine)
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture(autouse=True)
def mock_auth(client):
    with client.session_transaction() as sess:
        sess["authenticated"] = True


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
