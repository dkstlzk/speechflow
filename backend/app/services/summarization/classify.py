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

VALID_TYPES = frozenset([
    "meeting", "lecture", "interview", "presentation",
    "voice_note", "conversation", "unknown",
])


def classify_transcript(
    transcript: str,
    client: OllamaClient,
    model: str = "qwen2.5:3b",
    max_excerpt_chars: int = 1500,
) -> str:
    """Classify transcript type using a single LLM call on a short excerpt.

    Returns one of the VALID_TYPES strings. Falls back to 'unknown' on any error.
    """
    excerpt = transcript[:max_excerpt_chars].strip()
    if not excerpt:
        return "unknown"

    prompt = CLASSIFY_PROMPT.format(excerpt=excerpt)

    try:
        raw = client.generate(prompt, model=model)
    except OllamaClientError:
        logger.warning("Transcript classification failed, defaulting to unknown")
        return "unknown"

    parsed = raw.strip().lower().split("\n")[0].strip().rstrip(".")

    if parsed == "conversation":
        lower = transcript.lower()

        meeting_signals = [
            "attendance",
            "student success",
            "action item",
            "next steps",
            "meeting",
            "committee",
        ]

        if sum(term in lower for term in meeting_signals) >= 2:
            return "meeting"

    if parsed in VALID_TYPES:
        return parsed

    return "unknown"