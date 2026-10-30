"""Parse the tables out of a filing's HTML, keeping only what a reader sees.

Inline-XBRL tags (ix:nonFraction and friends) are unwrapped to their visible text and their attributes dropped:
the agent must find "capex" the way it would in a PDF, from row labels and headings, not from a us-gaap tag name.

For each table the parser keeps:
  - the text just above it (caption, unit line such as "(In millions, except per share data)"),
  - column headers built from the header rows, with colspans expanded so every value column gets its full label
    ("Three Months Ended | Jul 26, 2026"),
  - every row's label and the verbatim text of each value cell ("(1,234)", "—", "35,082").

Table IDs are positional ("t0042") and stable for an unchanged document and parser version.
"""
import html
import re
from html.parser import HTMLParser

PARSER_VERSION = "tables@15"  # 14: a filing that states no unit anywhere is whole dollars; 15: quarter-end date columns mark a quarterly table
_NUM = re.compile(r"^\(?-?\$?\s*\(?([0-9][0-9,]*(?:\.[0-9]+)?)\s*\)?%?$")
_DASHES = {"—", "–", "-", "— ", "−"}
_CCY = r"(?:USD\s+|US\$\s*|U\.S\.\s+dollars\s+|dollars\s+)?"
_UNIT = re.compile(r"\(\s*(?:in|dollars in|amounts in|\$ in|U\.S\. dollars in)\s+" + _CCY + r"(thousands|millions|billions)\b[^)]*\)", re.I)
# "($ millions)", and ExxonMobil's "(millions of dollars)": the unit word first, then the currency.
_UNIT_PAREN = re.compile(r"\(\s*(?:(?:US)?\$\s*(thousands|millions|billions)|(thousands|millions|billions)\s+of\s+(?:U\.?S\.?\s+)?dollars)\s*\)", re.I)
_UNIT_LOOSE = re.compile(r"\b(?:in|dollars in|amounts in)\s+" + _CCY + r"(thousands|millions|billions)\b", re.I)
# Coherent's "($000)" and "($000, except per share data)": three zeros for thousands.
_UNIT_000 = re.compile(r"\(\s*(?:US)?\$?\s*000(?:,000)*s?\b[^)]*\)", re.I)
# Bit Digital's "(Expressed in US dollars, except for the number of shares)": whole dollars, scale 1.
_UNIT_ONES = re.compile(r"\(\s*(?:expressed |amounts |stated |presented )?in\s+(?:U\.?S\.?\s+)?dollars\b(?!\s+in\s+(?:thousands|millions|billions))[^)]*\)", re.I)


def scale_of(unit_text: str) -> int:
    """"(in millions)" by the word; "($000)" and AT&T's "(000,000)" by counting the zeros."""
    m = re.search(r"thousands|millions|billions", unit_text, re.I)
    if m:
        return SCALES[m.group(0).lower()]
    zeros = len(re.sub(r"[^0]", "", unit_text))
    if zeros:
        return 1_000_000_000 if zeros >= 9 else 1_000_000 if zeros >= 6 else 1_000
    return 1  # "(expressed in US dollars)": whole dollars
_YEAR = re.compile(r"^(19|20)\d\d$")
SCALES = {"thousands": 1_000, "millions": 1_000_000, "billions": 1_000_000_000}


def parse_number(text: str) -> float | None:
    """Visible cell text -> number. Parentheses mean negative; a dash means zero. None if it isn't a number."""
    t = text.replace("\xa0", " ").replace("$", "").strip()
    if t in _DASHES or t == "":
        return 0.0 if t in _DASHES else None
    neg = t.startswith("(") or t.endswith(")") or t.startswith("-") or t.startswith("−")
    m = _NUM.match(t.replace("−", "-"))
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    return -v if neg else v


class _Collector(HTMLParser):
    """Collects tables (as rows of cells with colspans) and the plain text between them."""

    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self.text_since_table: list[str] = []
        self._depth = 0
        self._rows: list[list[tuple[str, int]]] = []
        self._row: list[tuple[str, int]] | None = None
        self._cell: list[str] | None = None
        self._span = 1
        self._hidden = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "ix:header" or (a.get("style") or "").replace(" ", "").lower().find("display:none") >= 0:
            self._hidden += 1 if tag in ("ix:header", "div", "span") else 0
            if tag in ("ix:header", "div", "span"):
                self._hide_tag = getattr(self, "_hide_tag", []) + [tag]
                return
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._rows = []
        elif self._depth and tag == "tr":
            self._row = []
        elif self._depth and tag in ("td", "th"):
            self._cell = []
            try:
                self._span = max(1, int(a.get("colspan") or 1))
            except ValueError:
                self._span = 1
        elif tag in self.BLOCK and not self._depth:
            self.text_since_table.append("\n")

    def handle_endtag(self, tag):
        if getattr(self, "_hide_tag", None) and tag == self._hide_tag[-1] and self._hidden:
            self._hide_tag.pop()
            self._hidden -= 1
            return
        if tag == "table" and self._depth:
            self._depth -= 1
            if self._depth == 0:
                before = re.sub(r"\s+", " ", " ".join(self.text_since_table[-60:])).strip()
                self.tables.append({"rows": self._rows, "before": before[-600:]})
                self.text_since_table = []
        elif self._depth and tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append((re.sub(r"\s+", " ", "".join(self._cell)).strip(), self._span))
            self._cell = None
        elif self._depth and tag == "tr" and self._row is not None:
            self._rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._hidden:
            return
        if self._cell is not None:
            self._cell.append(data)
        elif not self._depth:
            self.text_since_table.append(data)


def _cells(row: list[tuple[str, int]]) -> list[tuple[int, str]]:
    """(slot, text) for each non-empty cell, with '$' cells dropped and a lone ')' or '%' glued to the number before it."""
    out: list[tuple[int, str]] = []
    slot = 0
    for text, span in row:
        if text in (")", "%", ")%") and out:
            s, prev = out[-1]
            out[-1] = (s, prev + text)
        elif text and text != "$":
            out.append((slot, text))
        slot += span
    return out


def _structure(raw: dict, idx: int) -> dict | None:
    rows = [r for r in raw["rows"] if any(t for t, _ in r)]
    if len(rows) < 2:
        return None
    # Header rows: rows before the first row that has a label plus at least one number.
    # A row of bare years ("2026 2025 2024") is a header, not data.
    def is_data(r):
        c = _cells(r)
        nums = [t for _, t in c[1:] if parse_number(t) is not None]
        return bool(c) and parse_number(c[0][1]) is None and nums and not all(_YEAR.match(t) for t in nums)
    first_data = next((i for i, r in enumerate(rows) if is_data(r)), None)
    if first_data is None:
        return None
    # Data rows: label plus (slot, text) for each number.
    parsed = []
    for r in rows[first_data:]:
        c = _cells(r)
        if not c:
            continue
        if parse_number(c[0][1]) is not None:  # a row with no label (e.g. a subtotal line)
            label, values = "", c
        else:
            label, values = c[0][1], c[1:]
        parsed.append((label, [(s, x) for s, x in values if parse_number(x) is not None]))
    # Value columns: the slot positions of the row with the most numbers. Other rows snap to the nearest position.
    widest = max((n for _, n in parsed), key=len, default=[])
    positions = [s for s, _ in widest]
    if not positions:
        return None
    k = len(positions)

    def snap(nums):
        out, taken = [], set()
        for s, x in nums:
            order = sorted(range(k), key=lambda i: abs(positions[i] - s))
            i = next((i for i in order if i not in taken), order[0])
            taken.add(i)
            out.append((i, x))
        return out

    # Column labels, one header row at a time. A header row with exactly k cells maps by order (its spans are often
    # shifted against the numbers); otherwise each position takes the header cell covering it, or the nearest one.
    labels = [[] for _ in range(k)]
    for r in rows[:first_data]:
        cells, slot = [], 0
        for text, span in r:
            if text and text != "$" and not _UNIT.search(text) and not _UNIT_PAREN.fullmatch(text.strip()) and not _UNIT_000.fullmatch(text.strip()) and not _UNIT_ONES.fullmatch(text.strip()):
                cells.append((slot, slot + span, text))
            slot += span
        inner = [c for c in cells if c[0] > 0]  # cells in the label column are section labels ("Revenue:")
        if len(cells) == k:
            use = cells
        elif len(inner) == k:
            use = inner
        else:
            use = None
        if use:
            for i, c in enumerate(use):
                labels[i].append(c[2])
        elif inner and len(inner) > 1 and k % len(inner) == 0:
            # Group headers ("Three Months Ended" over 2 columns, "Six Months Ended" over 2): equal groups, in order.
            g = k // len(inner)
            for i in range(k):
                labels[i].append(inner[i // g][2])
        elif inner:
            for i, p in enumerate(positions):
                hit = [c for c in inner if c[0] <= p < c[1]] or [min(inner, key=lambda c: min(abs(p - c[0]), abs(p - (c[1] - 1))))]
                labels[i].append(hit[0][2])
    columns = []
    for i in range(k):
        head = " | ".join(dict.fromkeys(labels[i]))
        col_vals = [x for _, n in parsed for j, x in snap(n) if j == i]
        if not head and col_vals and all(re.fullmatch(r"\d{1,2}", x) for x in col_vals):
            head = "Note"
        columns.append(head or f"column {i + 1}")

    unit_text = None
    for src in [raw["before"][-300:]] + [" ".join(t for t, _ in r) for r in rows[:first_data + 2]]:
        m = _UNIT.search(src) or _UNIT_PAREN.search(src) or _UNIT_LOOSE.search(src) or _UNIT_000.search(src) or _UNIT_ONES.search(src)
        if m:
            unit_text = m.group(0)
    body = [{"label": label, "cells": [{"col": i, "text": x, "value": parse_number(x)} for i, x in snap(nums)]}
            for label, nums in parsed if nums or label]
    if not any(r["cells"] for r in body):
        return None
    return {"id": f"t{idx:04d}", "before": raw["before"][-300:], "unit_text": unit_text,
            "scale": scale_of(unit_text) if unit_text else None,
            "columns": columns, "rows": body}


def parse_tables(doc: bytes | str) -> list[dict]:
    text = doc.decode("utf-8", errors="replace") if isinstance(doc, bytes) else doc
    c = _Collector()
    c.feed(text)
    out = []
    for i, raw in enumerate(c.tables):
        t = _structure(raw, i)
        if t:
            out.append(t)
    return out


def document_units(doc: bytes | str) -> list[dict]:
    """Every unit statement in the document's visible text ("in USD thousands", "($ thousands)"), with context.
    Used when a statement table states no unit of its own (decision 2026-10-27: an agent may cite a unit stated
    elsewhere in the same filing; it is flagged as a warning)."""
    text = doc.decode("utf-8", errors="replace") if isinstance(doc, bytes) else doc
    text = re.sub(r"<ix:header>.*?</ix:header>", " ", text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)))
    out = []
    for rx in (_UNIT, _UNIT_PAREN, _UNIT_000, _UNIT_ONES):
        for m in rx.finditer(text):
            out.append({"text": m.group(0), "scale": scale_of(m.group(0)), "offset": m.start(),
                        "context": text[max(0, m.start() - 120):m.end() + 40].strip()})
    return sorted(out, key=lambda u: u["offset"])

