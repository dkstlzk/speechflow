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

    def generate(self, prompt: str, model: str = "qwen2.5:3b") -> str:
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

    client = QueueOllamaClient(["summary", "mom", "actions"])
    processor = TranscriptProcessor(ollama_client=client)

    assert processor.generate_summary(1) == "summary"
    assert processor.generate_mom(1) == "mom"
    assert processor.generate_action_items(1) == "actions"

    assert len(client.calls) == 3
    expected_transcript = (
        "Participant A: Hello everyone.\nParticipant B: Let's begin.\nParticipant C: We should also review the recent progress on the API integration so that everyone is up to date."
    )

    assert "Generate a structured executive summary" in client.calls[0]["prompt"]
    assert expected_transcript in client.calls[0]["prompt"]

    assert "Generate concise bullet-point takeaways" in client.calls[1]["prompt"]
    assert expected_transcript in client.calls[1]["prompt"]

    assert "Extract action items" in client.calls[2]["prompt"]
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

    client = QueueOllamaClient(["summary_part1", "summary_part2", "merged_summary"])
    processor = TranscriptProcessor(ollama_client=client)

    result = processor.generate_summary(3)

    assert result == "merged_summary"
    assert len(client.calls) == 3
    assert "A" * 6000 in client.calls[0]["prompt"]
    assert "B" * 6000 in client.calls[1]["prompt"]
    assert "--- PART 1 ---\nsummary_part1" in client.calls[2]["prompt"]
    assert "--- PART 2 ---\nsummary_part2" in client.calls[2]["prompt"]
    assert "Partial Summaries:" in client.calls[2]["prompt"]


def test_classify_transcript_returns_type(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    client = QueueOllamaClient(["meeting"])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.classify(1)
    assert result == "meeting"
    assert len(client.calls) == 1


def test_process_session_meeting(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    # classify -> meeting, summary, mom, action_items
    client = QueueOllamaClient(["meeting", "the summary", "the mom", "the actions"])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.process_session(1)
    assert result["transcript_type"] == "meeting"
    assert result["summary"] == "the summary"
    assert result["mom"] == "the mom"
    assert result["action_items"] == "the actions"


def test_process_session_lecture_skips_mom_and_actions(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.summarization.transcript_processor.get_session_transcript",
        lambda _session_id: _sample_payload(),
    )
    # classify -> lecture, summary only
    client = QueueOllamaClient(["lecture", "lecture summary"])
    processor = TranscriptProcessor(ollama_client=client)
    result = processor.process_session(1)
    assert result["transcript_type"] == "lecture"
    assert result["summary"] == "lecture summary"
    assert result["mom"] is None
    assert result["action_items"] is None

