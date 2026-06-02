"""Prompt templates for transcript intelligence generation."""

SUMMARY_PROMPT = """
Generate a compressed meeting summary.

Rules:

- Use only information present in the transcript.
- Do not add external knowledge.
- Do not repeat information.
- Do not expand information.
- Do not narrate the conversation.
- Organize information by topic.
- Prefer information compression over explanation.
- Omit topics with no meaningful content.

Do NOT write phrases such as:
- "Participants discussed..."
- "During the meeting..."
- "The discussion focused on..."
- "The meeting covered..."

If the transcript contains only one meaningful idea:
Return a single sentence.

If there is no meaningful discussion:
Return exactly:
No substantive discussion identified.

Otherwise return:

Overview
<one sentence>

Key Topics

<Topic Name>
- point
- point

<Topic Name>
- point

People Referencing Rules:

- Never output SPEAKER_XX identifiers.
- Prefer real names if explicitly mentioned.
- Prefer real roles if explicitly mentioned.
- Otherwise use participant labels already present.

Transcript:
{transcript}
"""


MOM_PROMPT = """
Generate meeting minutes.

Rules:

- Extract only information explicitly stated.
- Do not infer attendees.
- Do not infer decisions.
- Do not infer next steps.
- Do not infer ownership.
- Do not infer deadlines.
- Prefer omission over guessing.
- Omit empty sections entirely.

Attendees section is OPTIONAL.

Only include attendees if explicitly identified.

Do NOT:
- derive attendees from speaker labels
- derive attendees from diarization speakers
- create placeholder attendees

People Referencing Rules:

- Never output SPEAKER_XX identifiers.
- Prefer real names if explicitly mentioned.
- Prefer real roles if explicitly mentioned.
- Otherwise use participant labels already present.

Output format:

Attendees
- attendee

Decisions
- decision

Next Steps
- next step

Transcript:
{transcript}
"""


ACTION_ITEMS_PROMPT = """
Extract action items.

Rules:

- Include only actions that were:
  - assigned
  - agreed upon
  - committed to
  - accepted

Do NOT extract:
- suggestions
- recommendations
- possibilities
- ideas under discussion
- hypothetical actions

Do not infer:
- tasks
- owners
- deadlines

Keep items concise.

If no valid action items exist:
Return exactly:
No action items identified.

People Referencing Rules:

- Never output SPEAKER_XX identifiers.
- Prefer real names if explicitly mentioned.
- Prefer real roles if explicitly mentioned.
- Otherwise use participant labels already present.

Output format:

Action Items
- action
- action

Transcript:
{transcript}
"""


SUMMARY_MERGE_PROMPT = """
Merge partial summaries.

Rules:

- Merge duplicate topics.
- Remove repetition.
- Remove filler.
- Keep only unique information.
- Do not add information.
- Do not narrate the conversation.
- Preserve topic structure.
- Final output must be shorter than the combined inputs.

Output format:

Overview
<one sentence>

Key Topics

<Topic Name>
- point
- point

Partial Summaries:
{partial_outputs}
"""


MOM_MERGE_PROMPT = """
Merge partial meeting minutes.

Rules:

- Deduplicate attendees.
- Deduplicate decisions.
- Deduplicate next steps.
- Omit empty sections.
- Do not add information.
- Prefer omission over guessing.

Partial MoMs:
{partial_outputs}
"""


ACTION_ITEMS_MERGE_PROMPT = """
Merge partial action-item lists.

Rules:

- Remove duplicates.
- Merge equivalent actions.
- Keep wording concise.
- Do not invent actions.
- Preserve only agreed or assigned actions.

If no actions remain:
Return exactly:
No action items identified.

Output format:

Action Items
- action
- action

Partial Action Items:
{partial_outputs}
"""