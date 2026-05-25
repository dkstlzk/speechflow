from pyannote.audio import Pipeline
from dotenv import load_dotenv
import os

load_dotenv(".env")

token = os.getenv("HF_TOKEN")

print("Loaded token:", token[:10] + "...")

print("Loading pyannote pipeline...")

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=token
)

print("Pipeline loaded successfully!")