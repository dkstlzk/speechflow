import time
from typing import Optional
import torch
import numpy as np
from ...config.logging import get_logger
from ...services.transcription.streaming import SpeechSegment
from .worker_state import vad_model

logger = get_logger(__name__)

SILENCE_THRESHOLD_SECONDS = 1.5
MAX_SEGMENT_SECONDS = 10.0
VAD_SPEECH_THRESHOLD = 0.35

def _check_vad_speaking(audio_np: np.ndarray, sample_rate: int) -> bool:
    if vad_model is None:
        return True

    if len(audio_np) < sample_rate:
        return True

    try:
        last_second = audio_np[-sample_rate:]
        chunk_size = 512 if sample_rate == 16000 else 256

        for i in range(0, len(last_second), chunk_size):
            vad_chunk = last_second[i : i + chunk_size]
            if len(vad_chunk) != chunk_size:
                continue

            vad_tensor = torch.from_numpy(vad_chunk)
            speech_prob = vad_model(vad_tensor, sample_rate).item()

            if speech_prob > VAD_SPEECH_THRESHOLD:
                return True

        return False

    except Exception as e:
        logger.warning(f"[VAD Warning] {e}")
        return True

def check_segment_boundary(sid: str, session) -> Optional[SpeechSegment]:
    current_buf_len = len(session.audio_buffer)
    segment_bytes = current_buf_len - session.segment_start_offset
    bytes_per_sec = session.sample_rate * 2

    if segment_bytes < bytes_per_sec * 0.5 and not session.is_ending:
        return None

    segment_duration = segment_bytes / bytes_per_sec
    now = time.time()

    segment_audio = session.audio_buffer[session.segment_start_offset:]
    audio_np = (
        np.frombuffer(bytes(segment_audio), dtype=np.int16).astype(np.float32)
        / 32768.0
    )

    is_speaking = _check_vad_speaking(audio_np, session.sample_rate)

    if is_speaking:
        session.last_speech_time = now
        session.has_speech = True

    silence_duration = now - session.last_speech_time

    reason = None
    if session.is_ending:
        reason = "END"
    elif silence_duration >= SILENCE_THRESHOLD_SECONDS and getattr(session, "has_speech", False):
        reason = "SILENCE"
    elif segment_duration >= MAX_SEGMENT_SECONDS:
        reason = "MAX_LENGTH"

    if reason is None:
        return None

    end_time = session.segment_start_time + segment_duration

    segment = SpeechSegment(
        start_offset=session.segment_start_offset,
        end_offset=current_buf_len,
        start_time=session.segment_start_time,
        end_time=end_time,
    )

    logger.info(
        f"[Segmenter] Segment closed | Reason: {reason} "
        f"| Duration: {segment_duration:.1f}s "
        f"| Chunk #{session.chunk_index}"
    )

    return segment
