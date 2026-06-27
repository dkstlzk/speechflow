from backend.app.schemas.response import ApiResponse
from backend.app.services.summarization.transcript_processor import (
    TranscriptNotFoundError,
    EmptyTranscriptError,
    TranscriptGenerationError,
)

def test_process_session_success(client, monkeypatch):
    class DummySession:
        id = 12
        status = "completed"
    
    class DummyQuery:
        def with_for_update(self): return self
        def filter(self, *args): return self
        def first(self): return DummySession()
        def update(self, *args, **kwargs): return 1
    
    class DummyDB:
        def query(self, *args): return DummyQuery()
        def commit(self): pass
        def close(self): pass

    monkeypatch.setattr("backend.app.api.sessions.SessionLocal", DummyDB, raising=False)
    monkeypatch.setattr("backend.app.db.session.SessionLocal", DummyDB)
    monkeypatch.setattr("multiprocessing.get_context", lambda *a, **kw: type("MockContext", (), {"Process": lambda self, *a, **kw: type("MockProcess", (), {"start": lambda self: None})()})())

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 202
    payload = response.get_json()
    assert payload["success"] is True
    assert "message" in payload["data"]


def test_process_session_invalid_id(client):
    response = client.post("/api/sessions/xyz/process")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "invalid session id" in payload["error"].lower()


def test_process_session_not_found(client, monkeypatch):
    class DummyQuery:
        def with_for_update(self): return self
        def filter(self, *args): return self
        def first(self): return None
    
    class DummyDB:
        def query(self, *args): return DummyQuery()
        def close(self): pass

    monkeypatch.setattr("backend.app.api.sessions.SessionLocal", DummyDB, raising=False)
    monkeypatch.setattr("backend.app.db.session.SessionLocal", DummyDB)

    response = client.post("/api/sessions/999/process")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_get_summary_found(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.sessions.get_summary",
        lambda sid: {"session_id": sid, "summary": "test", "mom": None, "created_at": None},
    )
    response = client.get("/api/sessions/1/summary")
    assert response.status_code == 200
    assert response.get_json()["data"]["summary"] == "test"


def test_get_summary_not_found(client, monkeypatch):
    monkeypatch.setattr("backend.app.api.sessions.get_summary", lambda sid: None)
    response = client.get("/api/sessions/1/summary")
    assert response.status_code == 200
    assert response.get_json()["data"]["exists"] is False


def test_parse_action_items_text():
    from backend.app.utils.text import _parse_action_items_text

    raw = """Action Items
- Fix the deployment script
- Update the documentation
"""
    result = _parse_action_items_text(raw)
    assert len(result) == 2
    assert result[0] == "Fix the deployment script"
    assert result[1] == "Update the documentation"


def test_parse_action_items_no_items():
    from backend.app.utils.text import _parse_action_items_text

    assert _parse_action_items_text("No action items identified.") == []
    assert _parse_action_items_text("") == []
    assert _parse_action_items_text(None) == []
