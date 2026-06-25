def _parse_action_items_text(raw: str) -> list[str]:
    """Parse the raw action items text into a list of individual items."""
    if not raw or raw.strip().lower() == "no action items identified.":
        return []
    items = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            line = line[2:].strip()
        elif line.startswith("* "):
            line = line[2:].strip()
        if line.lower() == "no action items identified.":
            continue
        if line and line.lower() not in ("action items", "action items:"):
            items.append(line)
    return items
