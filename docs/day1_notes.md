# Day 1 Notes — SpeechFlow

## Objective
Set up and validate the complete local AI speech processing stack for the SpeechFlow MVP.

---

# Environment Setup

## OS
- Ubuntu Linux

## Python
- Python 3.11.15

### Why Python 3.11?
Initially attempted setup on Python 3.13, but switched to Python 3.11 due to better compatibility with:
- pyannote.audio
- PyTorch ecosystem
- speech/audio processing libraries
- faster-whisper dependencies

This reduced potential dependency instability and future installation issues.

---

# Project Environment

## Virtual Environment
- `.sf-env`

## CPU-only Architecture
The entire setup was configured for CPU-only inference.

### Reasoning
- avoids CUDA/GPU dependency complexity
- easier reproducibility
- lightweight MVP deployment
- compatible with most local systems

Verified no CUDA/NVIDIA dependencies remained inside the environment.

---

# Installed Core Components

## Backend
- FastAPI
- Uvicorn
- SQLAlchemy
- psycopg2-binary
- WebSockets

## Audio Processing
- FFmpeg
- Pydub
- ffmpeg-python

## Speech AI
- faster-whisper
- pyannote.audio
- Silero VAD

## Local LLM
- Ollama
- phi3:mini

---

# Backend Validation

## FastAPI Validation
Successfully launched FastAPI server locally.

### Verified
- root endpoint
- OpenAPI docs
- automatic schema generation

---

# Whisper Validation

## Model
- `small.en`

## Device
- CPU

## Compute Type
- int8 quantization

---

## Audio Pipeline Tested

### Input
- MP4 video file

### Processing Flow
MP4 Upload
→ FFmpeg audio extraction
→ WAV normalization
→ Whisper transcription

---

## FFmpeg Validation

Successfully tested:
- MP4 → WAV extraction
- mono conversion
- 16kHz normalization

Command used:

```bash
ffmpeg -i test_audio/meeting.mp4 \
-ac 1 \
-ar 16000 \
temp/output.wav
```

---

# Whisper Benchmark

## Audio Length
~37 seconds

## Inference Time
~3.37 seconds

## Realtime Factor
Inference faster than realtime on CPU-only setup.

Approximate realtime factor:
~11x realtime speed

---

# Whisper Observations

## Accuracy
Observed:
- good sentence segmentation
- punctuation generation
- strong conversational transcription quality

Minor inaccuracies:
- occasional proper noun variation
- capitalization differences

Overall transcription quality was highly usable for MVP purposes.

---

# Ollama Validation

## Model
- phi3:mini

## Tasks Tested
- transcript summarization
- structured extraction
- meeting-style summarization
- action item extraction

---

# Ollama Observations

## Positive
- coherent summaries
- good contextual understanding
- successful structured outputs
- low response latency (~3 seconds)

## Limitations Observed
- tendency to over-explain
- inferred reasoning beyond transcript
- verbose outputs in some prompts

Future improvements may require:
- prompt engineering
- concise output modes
- hallucination reduction constraints

---

# pyannote Validation

## HuggingFace Setup
- created HF access token
- accepted gated repository access
- configured `.env`

Validated:
- HuggingFace authentication
- gated model access
- pyannote pipeline initialization

---

# pyannote Pipeline Validation

Successfully loaded:
- `speaker-diarization-3.1`
- segmentation models
- PLDA dependencies

Pipeline initialization completed successfully on CPU.

---

# Architecture Validated

The following end-to-end pipeline was successfully validated locally:

MP4 Upload
→ FFmpeg preprocessing
→ Whisper transcription
→ pyannote diarization
→ Ollama transcript intelligence
→ Summary / MOM / Action Items

---

# Key Technical Decisions

## Chosen Whisper Model
- `small.en`

### Reasoning
- significantly faster than medium/large models
- acceptable transcription quality
- feasible on CPU-only setup

---

## Quantization
- int8 compute type

### Benefit
- reduced CPU memory usage
- faster inference speed

---

# Known Risks / Future Considerations

## pyannote Dependency Fragility
Observed:
- gated model dependencies
- changing APIs
- token/authentication requirements

Future mitigation:
- strict version pinning
- reproducible requirements management

---

## CPU Limitations
Potential future bottlenecks:
- long meeting processing
- realtime diarization scaling
- concurrent users

Possible future improvements:
- optional GPU support
- batching
- model optimization

---

# Overall Day 1 Outcome

Successfully validated the complete local speech AI stack required for the SpeechFlow MVP.

Core functionality confirmed:
- speech transcription
- audio preprocessing
- transcript summarization
- diarization pipeline
- local inference architecture

The project backend foundation is now stable enough to proceed into:
- upload endpoints
- service abstractions
- transcript persistence
- structured backend architecture