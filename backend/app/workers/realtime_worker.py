import time
import numpy as np
from flask_socketio import SocketIO

from ..services.transcription.streaming import session_manager
from ..services.transcription.whisper_service import WhisperTranscriptionService

# 1. Load Whisper EXACTLY ONCE outside the loop to preserve VRAM/CPU
transcriber = WhisperTranscriptionService()

# The Transcript Stabilizer Heuristic
def compute_transcript_delta(old_text: str, new_text: str) -> str:
    """Simple heuristic to find overlap and return only new words."""
    if not old_text:
        return new_text
        
    # Lowercase and strip punctuation for safer matching
    import re
    def clean_words(text):
        return re.sub(r'[^\w\s]', '', text.lower()).split()
        
    old_words = clean_words(old_text)
    new_words = clean_words(new_text)
    
    # Find the largest overlap where the end of old matches the start of new
    max_overlap = 0
    for i in range(1, min(len(old_words), len(new_words)) + 1):
        if old_words[-i:] == new_words[:i]:
            max_overlap = i
            
    # If we found overlap, return ONLY the new words (preserving original casing)
    if max_overlap > 0:
        original_new_words = new_text.split()
        return " ".join(original_new_words[max_overlap:])
        
    # Safety Fallback: Whisper glitch prevention
    if len(new_words) < 3:
        return ""
        
    # If the new text is entirely subsumed in the old text (Whisper repeating itself)
    if new_text.lower().strip() in old_text.lower().strip():
        return ""
        
    return new_text

def realtime_worker_loop(socketio: SocketIO):
    print("[RealtimeWorker] Background loop started. Whisper is ready.")
    
    while True:
        # Wrap in list() to avoid "dictionary changed size during iteration" errors
        for sid, session in list(session_manager.active_sessions.items()):
            
            # Dynamically calculate what 1 second of audio looks like for this user
            bytes_per_second = session.sample_rate * 2
            
            # 2. DELTA EXTRACTION: Did they speak enough new audio to justify inference?
            if session_manager.has_new_audio(sid, min_bytes=bytes_per_second):
                
                # 3. CONTEXT EXTRACTION: Grab the trailing 5 seconds of the buffer
                context_bytes = session_manager.get_context_window(sid, window_seconds=5.0)
                if not context_bytes:
                    continue
                    
                # 4. RAM CONVERSION: Int16 bytes -> Float32 Array
                audio_np = np.frombuffer(context_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                
                try:
                    # 5. INFERENCE
                    result = transcriber.transcribe(audio_np)
                    
                    if result.text:
                        print(f"[Whisper | {sid[:6]}] {result.text}")
                        
                        # 6. EMIT (Format matches your frontend TranscriptSegment interface)
                        socketio.emit("partial_transcript", {
                            "speaker": "Speaker",
                            "text": result.text,
                            "start_time": 0.0,
                            "end_time": 0.0,
                            "is_partial": True,
                            "chunk_index": 0
                        }, to=sid)
                        
                except Exception as e:
                    print(f"[RealtimeWorker] Inference error for {sid}: {e}")

        # Sleep for 1 second before checking again
        time.sleep(1)