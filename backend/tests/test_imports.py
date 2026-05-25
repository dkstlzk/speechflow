print("Testing imports...")

import torch
print("torch OK")

from faster_whisper import WhisperModel
print("faster-whisper OK")

from fastapi import FastAPI
print("fastapi OK")

from silero_vad import load_silero_vad
print("silero-vad OK")

from pyannote.audio import Pipeline
print("pyannote OK")

print("ALL IMPORTS SUCCESSFUL")