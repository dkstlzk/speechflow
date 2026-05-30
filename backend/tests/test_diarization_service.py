import pytest

from backend.app.services.diarization.diarization_service import DiarizationService


def test_diarization_service_returns_segments(monkeypatch):
    expected = [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.0},
        {"speaker": "SPEAKER_01", "start": 1.0, "end": 2.0},
    ]

    monkeypatch.setattr(
        "backend.app.services.diarization.diarization_service.diarize_audio",
        lambda _audio_path: expected,
    )

    service = DiarizationService()
    assert service.diarize("sample.wav") == expected


def test_diarization_service_bubbles_exceptions(monkeypatch):
    def _raise(_audio_path):
        raise RuntimeError("diarization failed")

    monkeypatch.setattr(
        "backend.app.services.diarization.diarization_service.diarize_audio",
        _raise,
    )

    service = DiarizationService()
    with pytest.raises(RuntimeError, match="diarization failed"):
        service.diarize("sample.wav")
