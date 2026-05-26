from pyannote.audio import Pipeline
from dotenv import load_dotenv
import os

load_dotenv()

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=os.getenv("HF_TOKEN")
)

print("Running diarization...\n")

diarization = pipeline("temp/meeting.wav")

print("Detected Speakers:\n")

for segment, speaker in diarization.speaker_diarization:
    print(f"{segment.start:.1f}s -> {segment.end:.1f}s : {speaker}")