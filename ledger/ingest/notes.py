"""Where a 10-K explains why past years changed. Agents read tables only, so a restatement's reason sits in the
notes; this finds the first sentence that states it, for the reviewer."""
import html
import re

CUES = re.compile(r"\b(?:recast|retrospectively (?:revised|adjusted|applied)|differ from (?:the )?amounts previously reported|reclassified to conform)\b", re.I)


def restatement_note(page: str) -> str | None:
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    m = CUES.search(text)
    if not m:
        return None
    start = max(text.rfind(". ", 0, m.start()) + 2, m.start() - 400)
    end = text.find(". ", m.end())
    return text[start:end + 1 if end != -1 else m.end() + 300].strip()
