"""Lightweight prompt-based transcript type classifier."""

from typing import Optional

from ...config.logging import get_logger
from .ollama import OllamaClient, OllamaClientError

logger = get_logger("summarization")

CLASSIFY_PROMPT = """
Classify the following transcript excerpt into exactly one category.

Categories:
- meeting
- lecture
- interview
- presentation
- voice_note
- conversation
- unknown

Examples:

meeting:
- team discussion
- school staff discussion
- planning session
- status update
- committee discussion
- student success meeting

conversation:
- casual chat
- friends talking
- family discussion
- informal dialogue

lecture:
- one person teaching a topic

interview:
- question and answer format

presentation:
- one person presenting information

Rules:
- Return ONLY the category name, nothing else.
- Do not explain your choice.
- If unsure, return "unknown".

Transcript excerpt:
{excerpt}
"""

VALID_TYPES = frozenset(
    [
        "meeting",
        "lecture",
        "interview",
        "presentation",
        "voice_note",
        "conversation",
        "unknown",
    ]
)


def classify_transcript(
    transcript: str,
    client: OllamaClient,
    model: Optional[str] = None,
    max_excerpt_chars: int = 1500,
) -> str:
    """Classify transcript type using a single LLM call on a short excerpt.

    Returns one of the VALID_TYPES strings. Falls back to 'unknown' on any error.
    """
    from ...config.settings import settings
    model = model or settings.OLLAMA_MODEL

    t_len = len(transcript)
    if t_len <= max_excerpt_chars:
        excerpt = transcript.strip()
    else:
        chunk_size = max_excerpt_chars // 3
        mid_idx = t_len // 2
        beginning = transcript[:chunk_size]
        middle = transcript[mid_idx - chunk_size // 2 : mid_idx + chunk_size // 2]
        end = transcript[-chunk_size:]
        excerpt = f"{beginning}\n...\n{middle}\n...\n{end}".strip()

    if not excerpt:
        return "unknown"

    prompt = CLASSIFY_PROMPT.format(excerpt=excerpt)

    try:
        raw = client.generate(prompt, model=model)
    except OllamaClientError:
        logger.warning(
            "Transcript classification failed due to Ollama error, defaulting to unknown"
        )
        return "unknown"

    parsed = raw.strip().lower().split("\n")[0].strip().rstrip(".")

    if parsed in VALID_TYPES:
        return parsed

    return "unknown"
