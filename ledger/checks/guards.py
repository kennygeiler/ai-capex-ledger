"""Code guards on what a quote says about its own period: words that make a stated amount cover part of a year
(type 68) and words that make an outlook a multi-year program rather than a year's guidance (type 69). Used by the
taxonomy rows and by the proof board; they tag, they never change a number."""
import re

PART_YEAR = re.compile(r"\b(Q[1-4]|[1-4]Q|H[12]|(first|second|third|fourth) (quarter|half)|(first|last) (three|six|nine) months|nine months|six months|three months|quarter)\b", re.I)
PROGRAM = re.compile(r"joint venture|once completed|over the next|through 20\d\d|by 20\d\d|multi-?year|cumulative|total investment|over (two|three|four|five|ten|\d+) years|program", re.I)


def part_year(quote: str) -> str | None:
    """The words that make a stated amount cover part of a year, or None (type 68)."""
    m = PART_YEAR.search(quote or "")
    return m.group(0) if m else None


def program_words(quote: str) -> str | None:
    """Words that make an outlook statement a multi-year program or a deal size rather than a year's guidance (type 69)."""
    m = PROGRAM.search(quote or "")
    return m.group(0) if m else None
