from dataclasses import dataclass

from backend.app.services.transcription import WhisperTranscriptionService


@dataclass
class DummySegment:
    start: float
    end: float
    text: str


class DummyModel:
    def transcribe(self, _audio_path, **kwargs):
        segments = [
            DummySegment(start=0.0, end=1.0, text=" hello"),
            DummySegment(start=1.0, end=2.0, text="world "),
        ]
        return segments, None


def test_transcription_service_orders_segments():
    service = WhisperTranscriptionService(model=DummyModel())
    result = service.transcribe("dummy.wav")

    assert result.text == "hello world"
    assert result.segments[0]["order"] == 0
    assert result.segments[1]["order"] == 1
