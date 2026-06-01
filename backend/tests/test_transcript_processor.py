import pytest

from backend.app.services.summarization.transcript_processor import (
    EmptyTranscriptError,
    TranscriptNotFoundError,
    TranscriptProcessor,
)


class QueueOllamaClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, prompt: str, model: str = "phi3:mini") -> str:
        self.calls.append({"prompt": prompt, "model": model})
        if not self.responses:
            return ""
        return self.responses.pop(0)


def _sample_payload():
    return {
        "session_id": "1",
        "status": "completed",
        "transcript": [
            {
                "speaker": "SPEAKER_00",
                "start": 0.0,
                "end": 1.2,
                "text": "Hello everyone.",
                "order": 0,
            },
            {
                "speaker": "SPEAKER_01",
                "start": 1.2,
                "end": 2.4,
                "text": "Let's begin.",
                "order": 1,
            },
            {
                "speaker": "SPEAKER_02",
                "start": 2.4,
                "end": 2.9,
                "text": "",
                "order": 2,
            },
        ],
    }


def test_transcript_processor_assembles_transcript(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )

    processor = TranscriptProcessor(ollama_client=QueueOllamaClient(["ok"]))
    assembled = processor.assemble_transcript(1)

    assert (
        assembled
        == "SPEAKER_00: Hello everyone.\nSPEAKER_01: Let's begin."
    )


def test_transcript_processor_generation_calls_ollama(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )

    client = QueueOllamaClient(["summary", "mom", "actions"])
    processor = TranscriptProcessor(ollama_client=client)

    assert processor.generate_summary(1) == "summary"
    assert processor.generate_mom(1) == "mom"
    assert processor.generate_action_items(1) == "actions"

    assert len(client.calls) == 3
    expected_transcript = (
        "SPEAKER_00: Hello everyone.\nSPEAKER_01: Let's begin."
    )

    assert "Summary:" in client.calls[0]["prompt"]
    assert expected_transcript in client.calls[0]["prompt"]

    assert "Attendees:" in client.calls[1]["prompt"]
    assert expected_transcript in client.calls[1]["prompt"]

    assert "Task | Owner | Deadline" in client.calls[2]["prompt"]
    assert expected_transcript in client.calls[2]["prompt"]


def test_transcript_processor_missing_session(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: None,
    )

    processor = TranscriptProcessor(ollama_client=QueueOllamaClient(["ok"]))
    with pytest.raises(TranscriptNotFoundError, match="Session 404 not found"):
        processor.assemble_transcript(404)


def test_transcript_processor_empty_transcript(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: {"session_id": "2", "status": "completed", "transcript": []},
    )

    processor = TranscriptProcessor(ollama_client=QueueOllamaClient(["ok"]))
    with pytest.raises(EmptyTranscriptError, match="no transcript chunks"):
        processor.assemble_transcript(2)
