import pytest

from backend.app.schemas.response import ApiResponse
from backend.app.services.summarization.transcript_processor import (
    TranscriptNotFoundError,
    EmptyTranscriptError,
    TranscriptGenerationError,
)

def test_process_session_success(client, monkeypatch):
    class DummyProcessor:
        def process_session(self, session_id):
            return {
                "session_id": session_id,
                "transcript_type": "meeting",
                "summary": "Fake summary",
                "mom": "Fake MOM",
                "action_items": "No action items identified.",
            }

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)
    monkeypatch.setattr("backend.app.api.sessions.save_summary", lambda *a, **kw: None)
    monkeypatch.setattr("backend.app.api.sessions.save_action_items", lambda *a, **kw: None)
    monkeypatch.setattr("backend.app.api.sessions.update_transcript_type", lambda *a, **kw: None)

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["session_id"] == 12
    assert payload["data"]["summary"] == "Fake summary"
    assert payload["data"]["transcript_type"] == "meeting"


def test_process_session_invalid_id(client):
    response = client.post("/api/sessions/xyz/process")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "invalid session id" in payload["error"].lower()


def test_process_session_not_found(client, monkeypatch):
    class DummyProcessor:
        def process_session(self, session_id):
            raise TranscriptNotFoundError("Session not found")

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/999/process")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_process_session_empty_transcript(client, monkeypatch):
    class DummyProcessor:
        def process_session(self, session_id):
            raise EmptyTranscriptError("Empty")

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "empty" in payload["error"].lower()


def test_process_session_generation_error(client, monkeypatch):
    class DummyProcessor:
        def process_session(self, session_id):
            raise TranscriptGenerationError("Ollama failed")

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert "failed" in payload["error"].lower()


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
    from backend.app.api.sessions import _parse_action_items_text

    raw = """Action Items
- Fix the deployment script
- Update the documentation
"""
    result = _parse_action_items_text(raw)
    assert len(result) == 2
    assert result[0] == "Fix the deployment script"
    assert result[1] == "Update the documentation"


def test_parse_action_items_no_items():
    from backend.app.api.sessions import _parse_action_items_text

    assert _parse_action_items_text("No action items identified.") == []
    assert _parse_action_items_text("") == []
    assert _parse_action_items_text(None) == []
