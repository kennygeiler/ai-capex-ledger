"""extraction_ids: the comma-joined list of extraction ids a value or a fact cites. The one reader of that column.

An extraction id is `accession|field|dimension|period_end` (or `accession|table|row|col` for a statement cell), and a
dimension or a cost-line label may itself hold a comma ("Land, buildings and leasehold improvements", "Fuel, purchased
power costs, and delivery fees"): a bare `.split(",")` cuts such an id in two and both halves miss (type 66, F-BF1)."""
from __future__ import annotations

import re

ID_START = re.compile(r"^\d{10}-\d{2}-\d{6}\|")


def split_ids(joined: str | None) -> list[str]:
    """The ids in a comma-joined extraction_ids string, a comma inside an id kept: a piece that does not start with an
    accession belongs to the id before it. Empty pieces are dropped; None or "" is []."""
    out: list[str] = []
    for piece in (joined or "").split(","):
        if out and ID_START.match(out[-1]) and not ID_START.match(piece):
            out[-1] += "," + piece
        elif piece:
            out.append(piece)
    return out
