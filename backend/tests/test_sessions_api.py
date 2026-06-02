import pytest

from backend.app.schemas.response import ApiResponse
from backend.app.services.summarization.transcript_processor import (
    TranscriptNotFoundError,
    EmptyTranscriptError,
    TranscriptGenerationError,
)

def test_process_session_success(client, monkeypatch):
    class DummyProcessor:
        def generate_summary(self, session_id):
            return "Fake summary"
        def generate_mom(self, session_id):
            return "Fake MOM"
        def generate_action_items(self, session_id):
            return "Fake actions"

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["session_id"] == 12
    assert payload["data"]["summary"] == "Fake summary"
    assert payload["data"]["mom"] == "Fake MOM"
    assert payload["data"]["action_items"] == "Fake actions"


def test_process_session_invalid_id(client):
    response = client.post("/api/sessions/xyz/process")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "invalid session id" in payload["error"].lower()


def test_process_session_not_found(client, monkeypatch):
    class DummyProcessor:
        def generate_summary(self, session_id):
            raise TranscriptNotFoundError("Session not found")

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/999/process")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_process_session_empty_transcript(client, monkeypatch):
    class DummyProcessor:
        def generate_summary(self, session_id):
            raise EmptyTranscriptError("Empty")

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "empty" in payload["error"].lower()


def test_process_session_generation_error(client, monkeypatch):
    class DummyProcessor:
        def generate_summary(self, session_id):
            raise TranscriptGenerationError("Ollama failed")

    monkeypatch.setattr("backend.app.api.sessions.TranscriptProcessor", DummyProcessor)

    response = client.post("/api/sessions/12/process")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert "failed" in payload["error"].lower()
