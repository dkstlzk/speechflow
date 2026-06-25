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

    def generate(self, prompt: str, model: str = "qwen2.5:3b", response_format: str = None) -> str:
        self.calls.append({"prompt": prompt, "model": model, "format": response_format})
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
                "text": " We should also review the recent progress on the API integration so that everyone is up to date.",
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
        == "Participant A: Hello everyone.\nParticipant B: Let's begin.\nParticipant C: We should also review the recent progress on the API integration so that everyone is up to date."
    )


def test_transcript_processor_generation_calls_ollama(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )

    client = QueueOllamaClient(['{"summary": "summary", "meeting_minutes": "mom", "action_items": "actions"}'])
    processor = TranscriptProcessor(ollama_client=client)

    data, timings = processor.generate_intelligence(1, processor.assemble_chunks(1))
    
    assert data.get("summary") == "summary"
    assert data.get("meeting_minutes") == "mom"
    assert data.get("action_items") == "actions"

    assert len(client.calls) == 1
    expected_transcript = (
        "Participant A: Hello everyone.\nParticipant B: Let's begin.\nParticipant C: We should also review the recent progress on the API integration so that everyone is up to date."
    )

    assert "executive summary, meeting takeaways, and action items" in client.calls[0]["prompt"]
    assert expected_transcript in client.calls[0]["prompt"]
    assert client.calls[0]["format"] == "json"


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

def test_transcript_processor_large_transcript_merging(monkeypatch):
    payload = {
        "session_id": "3",
        "status": "completed",
        "transcript": [
            {
                "speaker": "SPEAKER_00",
                "start": 0.0,
                "end": 1.0,
                "text": "A" * 6000,
                "order": 0,
            },
            {
                "speaker": "SPEAKER_01",
                "start": 1.0,
                "end": 2.0,
                "text": "B" * 6000,
                "order": 1,
            },
        ],
    }
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: payload,
    )

    client = QueueOllamaClient(['{"summary": "p1"}', '{"summary": "p2"}', '{"summary": "merged_summary"}'])
    processor = TranscriptProcessor(ollama_client=client)

    data, timings = processor.generate_intelligence(3, processor.assemble_chunks(3))

    assert data.get("summary") == "merged_summary"
    assert len(client.calls) == 3
    assert "A" * 6000 in client.calls[0]["prompt"]
    assert "B" * 6000 in client.calls[1]["prompt"]
    assert "--- PART 1 ---\n{\"summary\": \"p1\"}" in client.calls[2]["prompt"]
    assert "--- PART 2 ---\n{\"summary\": \"p2\"}" in client.calls[2]["prompt"]
    assert "Partial JSON Outputs:" in client.calls[2]["prompt"]


def test_classify_transcript_returns_type(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    client = QueueOllamaClient(["meeting"])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.classify(1, processor.assemble_chunks(1))
    assert result == "meeting"
    assert len(client.calls) == 1


def test_process_session_meeting(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    # classify -> meeting, generate_intelligence -> JSON string
    client = QueueOllamaClient(["meeting", '{"summary": "the summary", "meeting_minutes": "the mom", "action_items": "the actions"}'])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.process_session(1)
    assert result["transcript_type"] == "meeting"
    assert result["summary"] == "the summary"
    assert result["mom"] == "the mom"
    assert result["action_items"] == "the actions"


def test_process_session_lecture_skips_mom_but_keeps_actions(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    # classify -> lecture, generate_intelligence -> JSON string
    client = QueueOllamaClient(["lecture", '{"summary": "lecture summary", "meeting_minutes": "ignore", "action_items": "read a book"}'])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.process_session(1)
    assert result["transcript_type"] == "lecture"
    assert result["summary"] == "lecture summary"
    assert result["mom"] is None
    assert result["action_items"] == "read a book"

def test_process_session_json_fallback_failure(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    # classify -> meeting, generate_intelligence -> invalid JSON string
    client = QueueOllamaClient(["meeting", "{bad json"])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.process_session(1)
    
    assert result["transcript_type"] == "meeting"
    assert result["summary"] == "{bad json"
    assert result["mom"] is None
    assert result["action_items"] is None
