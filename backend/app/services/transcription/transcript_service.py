"""Transcript orchestration service.

Handles alignment, chunk ordering, and transcript reconstruction.
"""

from typing import Dict, List, Optional, Tuple


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _normalize_transcript_segments(transcript_segments: List[Dict]) -> List[Dict]:
    normalized: List[Dict] = []
    for index, segment in enumerate(transcript_segments):
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end < start:
            end = start

        try:
            order = int(segment.get("order", index))
        except (TypeError, ValueError):
            order = index

        normalized.append(
            {
                "start": start,
                "end": end,
                "text": str(segment.get("text", "")).strip(),
                "order": order,
                "_input_index": index,
            }
        )

    normalized.sort(
        key=lambda item: (
            item["order"],
            item["start"],
            item["end"],
            item["_input_index"],
        )
    )
    return normalized


def _normalize_speaker_segments(
    speaker_segments: List[Dict], default_speaker: str
) -> List[Dict]:
    normalized: List[Dict] = []
    for index, segment in enumerate(speaker_segments):
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end <= start:
            continue

        speaker = str(segment.get("speaker") or default_speaker).strip() or default_speaker
        normalized.append(
            {
                "speaker": speaker,
                "start": start,
                "end": end,
                "_input_index": index,
            }
        )

    normalized.sort(
        key=lambda item: (
            item["start"],
            item["end"],
            item["speaker"],
            item["_input_index"],
        )
    )
    return normalized


def _find_best_overlap_speaker(
    seg_start: float, seg_end: float, speaker_segments: List[Dict]
) -> Tuple[Optional[str], float]:
    overlap_by_speaker: Dict[str, float] = {}
    for speaker in speaker_segments:
        overlap = _overlap_seconds(seg_start, seg_end, speaker["start"], speaker["end"])
        if overlap <= 0.0:
            continue
        speaker_label = speaker["speaker"]
        overlap_by_speaker[speaker_label] = overlap_by_speaker.get(speaker_label, 0.0) + overlap

    if not overlap_by_speaker:
        return None, 0.0

    speaker_label, overlap = sorted(
        overlap_by_speaker.items(),
        key=lambda item: (-item[1], item[0]),
    )[0]
    return speaker_label, overlap


def align_transcript_with_speakers(
    transcript_segments: List[Dict],
    speaker_segments: List[Dict],
    default_speaker: str = "SPEAKER_00",
    min_overlap_seconds: float = 0.2,
    min_overlap_ratio: float = 0.1,
    switch_hysteresis_seconds: float = 0.35,
) -> List[Dict]:
    """Align Whisper segments with diarization output."""
    ordered_transcript = _normalize_transcript_segments(transcript_segments)
    if not ordered_transcript:
        return []

    ordered_speakers = _normalize_speaker_segments(speaker_segments, default_speaker)
    if not ordered_speakers:
        return [
            {
                "speaker": default_speaker,
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "order": seg["order"],
            }
            for seg in ordered_transcript
        ]

    last_speaker: Optional[str] = None
    aligned: List[Dict] = []
    unique_speakers = {item["speaker"] for item in ordered_speakers}
    single_speaker = len(unique_speakers) == 1
    single_speaker_label = next(iter(unique_speakers)) if single_speaker else None

    for segment in ordered_transcript:
        seg_start = float(segment["start"])
        seg_end = float(segment["end"])
        duration = max(seg_end - seg_start, 0.001)

        if single_speaker and single_speaker_label is not None:
            chosen = single_speaker_label
        else:
            best_speaker, best_overlap = _find_best_overlap_speaker(
                seg_start, seg_end, ordered_speakers
            )
            overlap_ratio = best_overlap / duration

            has_strong_overlap = bool(best_speaker) and (
                best_overlap >= min_overlap_seconds and overlap_ratio >= min_overlap_ratio
            )
            if has_strong_overlap:
                chosen = best_speaker
                if (
                    last_speaker is not None
                    and best_speaker != last_speaker
                    and best_overlap < switch_hysteresis_seconds
                ):
                    # Prevent rapid speaker flips from short, ambiguous overlaps.
                    chosen = last_speaker
            else:
                chosen = last_speaker or default_speaker

        last_speaker = chosen or default_speaker
        aligned.append(
            {
                "speaker": chosen or default_speaker,
                "start": seg_start,
                "end": seg_end,
                "text": segment["text"],
                "order": segment["order"],
            }
        )

    return aligned
