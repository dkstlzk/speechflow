"""Transcript orchestration service.

Handles alignment, chunk ordering, and transcript reconstruction.
"""

from typing import Dict, List


def align_transcript_with_speakers(
    transcript_segments: List[Dict], speaker_segments: List[Dict]
) -> List[Dict]:
    """Align Whisper segments with diarization output."""
    # TODO: implement timestamp overlap alignment.
    return transcript_segments
