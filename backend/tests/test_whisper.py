from faster_whisper import WhisperModel
import time

AUDIO_PATH = "./temp/meeting.wav"

model = WhisperModel(
    "small.en",
    device="cpu",
    compute_type="int8"
)

start = time.time()

segments, info = model.transcribe(AUDIO_PATH)

for segment in segments:
    print(
        f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}"
    )

end = time.time()

print(f"\nTime taken: {end - start:.2f} seconds")