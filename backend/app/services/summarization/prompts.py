"""Prompt templates for transcript intelligence generation."""

SUMMARY_PROMPT = """
Generate a structured executive summary of the transcript.
If the transcript contains test phrases,
microphone checks,
audio checks,
or very little meaningful content:

Return a short factual summary.

Do not invent context.
Do not infer topics.
Do not fabricate technical subjects.

Internal guidance:

- Use only information present in the transcript.
- Do not add external knowledge.
- Do not repeat information.
- Output should be substantially shorter than the transcript.
- Every bullet should represent multiple related statements when possible.
- Do not narrate the conversation.
- Identify the main topics first.
- Group related information under the same topic.
- Create a new topic only when the subject meaningfully changes.
- Prefer fewer high-quality topics over many small topics.
- Prefer information compression over explanation.
- Omit topics with no meaningful content.
- Do not explain why something happened.
- Do not infer motivations, causes, intentions, emotions, or outcomes.
- Report information only.

Do not output prompt instructions.
Do not output rule names.
Do not output explanation of formatting decisions.
Output only the final summary.

Single-Speaker Handling:

- Treat single-speaker transcripts as monologues or statements.

Output format MUST be EXACTLY:

Brief Overview
<2-4 sentence executive summary>

Key Points

• <Topic>
  - <supporting detail>
  - <supporting detail>

• <Topic>
  - <supporting detail>

If the transcript does not contain a coherent discussion, still summarize the content that is present under Brief Overview and omit Key Points if necessary.

Name Handling:
- Never output SPEAKER_XX identifiers.
- Prefer real names if mentioned.
- Avoid referring to people if no names are available.

Transcript:
{transcript}
"""


MOM_PROMPT = """
Generate concise bullet-point takeaways from the discussion.

Internal guidance:

- Extract only information explicitly stated.
- Focus on conclusions reached, important observations, and key discussion outcomes.
- Prefer omission over guessing.
- Omit empty sections entirely.
- Never output SPEAKER_XX identifiers.
- Do not generate attendee lists, action items, or task assignments.

Output format MUST be exactly:

Meeting Takeaways
• <takeaway>
• <takeaway>
• <takeaway>

If no takeaways exist, return exactly:
No meeting minutes identified.

Transcript:
{transcript}
"""


ACTION_ITEMS_PROMPT = """
Extract action items from the transcript.

Internal guidance:

- Include only actions that were assigned, agreed upon, committed to, or accepted.
- Do not convert suggestions into actions.
- Keep items concise.
- Never output SPEAKER_XX identifiers.

Output format MUST be exactly:

Action Items
• [Owner Name] -> [Actionable Task]
• [Actionable Task] (if no explicit owner)

If no valid action items exist, return exactly:
No action items identified.

Transcript:
{transcript}
"""


SUMMARY_MERGE_PROMPT = """
Merge partial summaries.

Internal guidance:
- Merge duplicate topics.
- Remove repetition.
- Keep only unique information.

Output format MUST be EXACTLY:

Brief Overview
<2-4 sentence executive summary>

Key Points

• <Topic>
  - <supporting detail>
  - <supporting detail>

Partial Summaries:
{partial_outputs}
"""


MOM_MERGE_PROMPT = """
Merge partial meeting takeaways.

Internal guidance:
- Deduplicate takeaways.
- Focus on conclusions reached, important observations, and key discussion outcomes.
- Omit empty sections.

Output format MUST be exactly:

Meeting Takeaways
• <takeaway>
• <takeaway>

Partial MoMs:
{partial_outputs}
"""


ACTION_ITEMS_MERGE_PROMPT = """
Merge partial action-item lists.

Internal guidance:
- Remove duplicates and merge equivalent actions.

Output format MUST be exactly:

Action Items
• [Owner] -> [Task]
• [Task]

Partial Action Items:
{partial_outputs}
"""