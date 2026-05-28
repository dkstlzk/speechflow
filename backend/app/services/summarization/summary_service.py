"""Transcript intelligence service."""

from typing import Dict

from .ollama import summarize_transcript


def generate_summary(transcript_text: str) -> Dict:
    """Generate summary, MOM, and action items from transcript text."""
    # TODO: implement prompt templates and fallback models.
    return summarize_transcript(transcript_text)
