from backend.app.services.transcription.transcript_service import (
    align_transcript_with_speakers,
)


def test_alignment_prefers_overlap():
    transcript = [
        {"start": 0.0, "end": 1.0, "text": "hello", "order": 0},
        {"start": 1.0, "end": 2.0, "text": "world", "order": 1},
    ]
    speakers = [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.1},
        {"speaker": "SPEAKER_01", "start": 1.1, "end": 2.1},
    ]

    aligned = align_transcript_with_speakers(transcript, speakers)

    assert aligned[0]["speaker"] == "SPEAKER_00"
    assert aligned[1]["speaker"] == "SPEAKER_01"


def test_alignment_falls_back_to_default_when_empty():
    transcript = [{"start": 0.0, "end": 1.0, "text": "hello", "order": 0}]

    aligned = align_transcript_with_speakers(transcript, [])

    assert aligned[0]["speaker"] == "SPEAKER_00"


def test_alignment_avoids_tiny_overlap_speaker_flip():
    transcript = [
        {"start": 0.0, "end": 1.0, "text": "first", "order": 0},
        {"start": 1.0, "end": 1.18, "text": "short", "order": 1},
    ]
    speakers = [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.05},
        {"speaker": "SPEAKER_01", "start": 1.05, "end": 1.25},
    ]

    aligned = align_transcript_with_speakers(transcript, speakers)

    assert aligned[0]["speaker"] == "SPEAKER_00"
    assert aligned[1]["speaker"] == "SPEAKER_00"


def test_alignment_handles_single_speaker_audio_with_gaps():
    transcript = [
        {"start": 0.0, "end": 0.6, "text": "segment one", "order": 0},
        {"start": 1.8, "end": 2.2, "text": "segment two", "order": 1},
    ]
    speakers = [{"speaker": "SPEAKER_42", "start": 0.0, "end": 0.2}]

    aligned = align_transcript_with_speakers(transcript, speakers)

    assert [segment["speaker"] for segment in aligned] == [
        "SPEAKER_42",
        "SPEAKER_42",
    ]


def test_alignment_returns_deterministic_order_from_unsorted_segments():
    transcript = [
        {"start": 2.0, "end": 2.5, "text": "third", "order": 2},
        {"start": 0.0, "end": 0.5, "text": "first", "order": 0},
        {"start": 1.0, "end": 1.5, "text": "second", "order": 1},
    ]
    speakers = [{"speaker": "SPEAKER_00", "start": 0.0, "end": 3.0}]

    aligned = align_transcript_with_speakers(transcript, speakers)

    assert [segment["order"] for segment in aligned] == [0, 1, 2]
    assert [segment["text"] for segment in aligned] == ["first", "second", "third"]
