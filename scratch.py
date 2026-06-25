from backend.app.db.session import SessionLocal
from backend.app.models.transcript_chunk import TranscriptChunk
from backend.app.services.translation import TranslationService
from backend.app.services.summarization.ollama import OllamaClient
from backend.app.config.settings import settings

db = SessionLocal()
chunks = db.query(TranscriptChunk).filter(TranscriptChunk.session_id == 449).all()

service = TranslationService(
    ollama_client=OllamaClient()
)

batch_chunks = [{"id": c.id, "text": c.text} for c in chunks]

print("Sending chunks:", batch_chunks)
prompt = f"""You are an expert translator. 
Translate the following JSON array of transcript chunks into Hindi.

Rules:
- You must return STRICT JSON and ONLY JSON. Do not use markdown blocks.
- The output must be a JSON array of objects, with the exact same "id" values as the input.
- Translate the "text" field to Hindi.
- Preserve context across chunks. Return exact same ids. Do not merge chunks. Do not reorder chunks.
- Use natural, modern, and conversational Hindi. Prefer commonly spoken words over overly formal terms.
- Do NOT translate technical terms unnecessarily. Keep terms like Meeting ID, WhatsApp, Email, Transcript, Summary, Action Items, Workflow, and Translation as-is when appropriate.
- The translation should sound like a professional meeting transcript written by a native speaker.

Input JSON:
{batch_chunks}

Output JSON format:
[
  {{"id": 1, "text": "translated text here"}},
  {{"id": 2, "text": "translated text here"}}
]
"""

res = service._client.generate(prompt, response_format="json")
print("Raw Ollama response:")
print(res)

import json
try:
    parsed = json.loads(res)
    print("Parsed JSON:", parsed)
except Exception as e:
    print("JSON Error:", e)
