import logging

from backend.app.services.diarization import pyannote as diarization_py


class DummyTurn:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class DummyAnnotation:
    def __init__(self, tracks):
        self._tracks = tracks

    def itertracks(self, yield_label=True):
        for start, end, speaker in self._tracks:
            yield DummyTurn(start, end), None, speaker


class DummyOutput:
    def __init__(self, annotation):
        self.speaker_diarization = annotation


class DummyOutputNoAttribute:
    def __init__(self, tracks):
        self._tracks = tracks

    def itertracks(self, yield_label=True):
        for start, end, speaker in self._tracks:
            yield DummyTurn(start, end), None, speaker


class DummyPipeline:
    def __init__(self, output):
        self._output = output

    def __call__(self, audio_path: str):
        return self._output


def test_diarize_audio_uses_speaker_diarization_attribute(monkeypatch):
    tracks = [
        (1.0, 2.0, "SPEAKER_01"),
        (0.0, 0.5, "SPEAKER_00"),
    ]
    output = DummyOutput(DummyAnnotation(tracks))
    pipeline = DummyPipeline(output)

    monkeypatch.setattr(diarization_py, "_get_pipeline", lambda: pipeline)

    segments = diarization_py.diarize_audio("sample.wav")

    assert segments == [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 0.5},
        {"speaker": "SPEAKER_01", "start": 1.0, "end": 2.0},
    ]


def test_diarize_audio_falls_back_to_output_when_missing_speaker_diarization(
    monkeypatch,
):
    tracks = [
        (0.0, 1.2, "SPEAKER_00"),
        (1.2, 2.1, "SPEAKER_01"),
    ]
    output = DummyOutputNoAttribute(tracks)
    pipeline = DummyPipeline(output)

    monkeypatch.setattr(diarization_py, "_get_pipeline", lambda: pipeline)

    segments = diarization_py.diarize_audio("sample.wav")

    assert segments == [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.2},
        {"speaker": "SPEAKER_01", "start": 1.2, "end": 2.1},
    ]


def test_diarize_audio_logs_community_output_metadata(monkeypatch, caplog):
    tracks = [
        (0.0, 0.6, "SPEAKER_00"),
        (0.6, 1.2, "SPEAKER_01"),
        (1.2, 1.8, "SPEAKER_00"),
    ]
    output = DummyOutput(DummyAnnotation(tracks))
    pipeline = DummyPipeline(output)

    monkeypatch.setattr(diarization_py, "_get_pipeline", lambda: pipeline)
    monkeypatch.setattr(
        diarization_py,
        "_PIPELINE_MODEL",
        "pyannote/speaker-diarization-community-1",
    )

    caplog.set_level(logging.INFO, logger="speechflow.diarization")
    diarization_py.diarize_audio("sample.wav")

    record = next(
        entry
        for entry in caplog.records
        if entry.getMessage() == "Diarization completed"
    )
    assert record.model_name == "pyannote/speaker-diarization-community-1"
    assert record.speaker_count == 2
    assert record.segment_count == 3
    assert hasattr(record, "duration_seconds")
