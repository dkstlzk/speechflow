import time
import torch
import numpy as np
from flask_socketio import SocketIO

from ..services.transcription.streaming import session_manager
from ..services.transcription.whisper_service import WhisperTranscriptionService
from ..services.persistence.transcripts import save_transcript_chunks

# 1. Load Whisper EXACTLY ONCE outside the loop to preserve VRAM/CPU
transcriber = WhisperTranscriptionService()

# 2. Load Silero VAD (ONNX Mode for ultra-fast CPU inference)
try:
    from silero_vad import load_silero_vad
    vad_model = load_silero_vad(onnx=True)
    print("[VAD] Silero VAD loaded successfully (ONNX CPU Mode).")
except Exception as e:
    print(f"[VAD] Error loading Silero VAD. Running in fallback mode. Error: {e}")
    vad_model = None

def realtime_worker_loop(socketio: SocketIO):
    print("[RealtimeWorker] Background loop started. AI is ready.")
    
    while True:
        # Wrap in list() to avoid "dictionary changed size during iteration" errors
        for sid, session in list(session_manager.active_sessions.items()):
            
            # Dynamically calculate what 1 second of audio looks like for this user
            bytes_per_second = session.sample_rate * 2
            
            # Since bytes always arrive (even background noise), we process them
            if session_manager.has_new_audio(sid, min_bytes=bytes_per_second):
                
                audio_window = session.audio_buffer
                # EMERGENCY NET: Force commit if they ramble for > 15s to save memory
                force_commit = len(audio_window) >= (bytes_per_second * 15)
                
                # RAM CONVERSION: Int16 bytes -> Float32 Array
                audio_np = np.frombuffer(audio_window, dtype=np.int16).astype(np.float32) / 32768.0
                
                # TRUE VAD CHECK 
                is_speaking = True # Default to true if VAD fails
                if vad_model is not None and len(audio_np) >= session.sample_rate:
                    try:
                        # Extract the last 1 second of audio
                        last_second = audio_np[-session.sample_rate:]
                        is_speaking = False
                        
                        # Silero strictly requires chunks of exactly 512 samples for 16kHz
                        chunk_size = 512 if session.sample_rate == 16000 else 256
                        
                        for i in range(0, len(last_second), chunk_size):
                            vad_chunk = last_second[i:i+chunk_size]
                            
                            # Only process full chunks
                            if len(vad_chunk) == chunk_size:
                                vad_tensor = torch.from_numpy(vad_chunk)
                                speech_prob = vad_model(vad_tensor, session.sample_rate).item()
                                
                                # If any 32ms micro-chunk contains speech, the user is talking
                                if speech_prob > 0.4:
                                    is_speaking = True
                                    break
                                    
                    except Exception as e:
                        print(f"[VAD Warning] {e}")
                        is_speaking = True
                
                # Update Silence Ticks
                if not is_speaking:
                    session.silence_ticks += 1
                else:
                    session.silence_ticks = 0

                try:
                    # INFERENCE
                    result = transcriber.transcribe(audio_np)
                    text = result.text.strip() if result.text else ""
                    
                    if text:
                        # 1. Stability Tracking
                        if text == session.current_transcript:
                            session.stability_ticks += 1
                        else:
                            session.current_transcript = text
                            session.stability_ticks = 0

                            socketio.emit(
                                "partial_transcript",
                                {
                                    "speaker": "UNKNOWN",
                                    "text": session.current_transcript,
                                    "start_time": session.commit_start_time,
                                    "end_time": session.commit_start_time,
                                    "chunk_index": session.chunk_index,
                                    "is_partial": True,
                                },
                                to=sid,
                            )
    
                        # --- 2. THE TRIPLE SAFETY NET COMMIT TRIGGER ---
                        # Primary: VAD says you stopped talking for 2 seconds
                        vad_commit = session.silence_ticks >= 2
                        # Fallback: Text hasn't changed in 4 seconds
                        stability_commit = session.stability_ticks >= 4
                        
                        if vad_commit or stability_commit or force_commit:
                            # Log exactly *why* the chunk was committed
                            reason = "VAD" if vad_commit else "STABILITY" if stability_commit else "FORCED"
                            print(f"[COMMIT | {reason}] {session.current_transcript}")
                            
                            try:
                                now = time.time()
                                start_time = session.commit_start_time

                                end_time = (
                                    now
                                    - session.recording_started_at
                                )

                                save_transcript_chunks(
                                    int(session.session_id),
                                    [
                                        {
                                            "session_id": int(session.session_id),
                                            "speaker_id": None,
                                            "start_time": start_time,
                                            "end_time": end_time,
                                            "text": session.current_transcript,
                                            "chunk_index": session.chunk_index,
                                            "is_partial": False,
                                        }
                                    ],
                                )

                                socketio.emit(
                                    "partial_transcript",
                                    {
                                        "speaker": "UNKNOWN",
                                        "text": session.current_transcript,
                                        "start_time": start_time,
                                        "end_time": end_time,
                                        "chunk_index": session.chunk_index,
                                        "is_partial": False,
                                    },
                                    to=sid,
                                )

                                session.commit_start_time = end_time
                                session.chunk_index += 1

                                print(
                                    f"[RealtimePersistence] Saved chunk #{session.chunk_index - 1}"
                                    f" ({start_time:.2f}s -> {end_time:.2f}s)"
                                )

                            except Exception as persist_error:
                                print(
                                    f"[RealtimePersistence] Failed to save transcript chunk: {persist_error}"
                                )
                            
                            # Clean up for the next sentence
                            session_manager.clear_buffer_for_next_commit(sid)
                            
                except Exception as e:
                    print(f"[RealtimeWorker] Inference error for {sid}: {e}")

        # Sleep for 1 second before checking again
        time.sleep(1)