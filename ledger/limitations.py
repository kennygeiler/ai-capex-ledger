"""What the data can't support (taxonomy/limitations.yaml, T68), and the LIMITATIONS.md every packet carries.

`load` refuses an entry without a field. A `rows: {computed: <name>}` count is read from the data by COMPUTED[name]
(the fault-test reports, failures.yaml, asset_types.yaml, config, and the packet's own CSVs), never typed by hand.
Paths are fixed at import, as failures.FILE is, so a test that points store.ROOT elsewhere still reads the repo's."""
import csv
import io
import json
import re
from pathlib import Path

import yaml

from .store import ROOT

FILE = ROOT / "taxonomy" / "limitations.yaml"
FAULTS = ROOT / "reports" / "stage3-faults.json"
FAULTS_XBRL_OFF = ROOT / "reports" / "stage3-faults-xbrl-off.json"
REQUIRED = ("weakness", "rows", "mitigation", "closes")
CLOSES = re.compile(r"^(none|T\d+[a-z]?)$")


def load(path: Path = FILE) -> list[dict]:
    """The entries in file order, each with `id` set; ValueError on a missing or empty field, a `rows` that is not an
    integer, `all` or `{computed: <known name>}`, or a `closes` that is not a ticket id or `none`."""
    raw = yaml.safe_load(path.read_text()) or {}
    out = []
    for key, e in raw.items():
        if not isinstance(e, dict):
            raise ValueError(f"limitations: {key!r} must be a mapping")
        missing = [k for k in REQUIRED if e.get(k) in (None, "")]
        if missing:
            raise ValueError(f"limitations: {key} is missing {missing}")
        r = e["rows"]
        if not (r == "all" or (isinstance(r, int) and not isinstance(r, bool)) or (isinstance(r, dict) and set(r) == {"computed"} and r["computed"] in COMPUTED)):
            raise ValueError(f"limitations: {key} has rows {r!r}; an integer, `all`, or computed: one of {sorted(COMPUTED)}")
        if not CLOSES.match(str(e["closes"])):
            raise ValueError(f"limitations: {key} closes {e['closes']!r}; a ticket id (T68) or none")
        out.append({"id": key, **{k: (" ".join(v.split()) if isinstance(v, str) else v) for k, v in e.items()}})
    return out


# ── the computed counts: each (files) -> (count or None, what it counts). None when the source is missing ─────────────
def _report(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _escapes(kind: str) -> tuple:
    d = _report(FAULTS_XBRL_OFF)
    k = ((d or {}).get("by_kind") or {}).get(kind)
    if not k:
        return None, f"not measured ({FAULTS_XBRL_OFF.name} missing)"
    return k["escaped"], f"of {k['planted']} planted {kind} trials, with the XBRL comparison removed"


def _csv(files, name) -> list[dict]:
    text = (files or {}).get(name) or ""
    return list(csv.DictReader(io.StringIO(text))) if text.strip() else []


def _agree(files) -> tuple:
    rows = _csv(files, "values.csv")
    return sum(r.get("check_label") == "agree" for r in rows), f"of {len(rows)} values in values.csv agree with the filer's XBRL"


def _outside(files) -> tuple:
    from .config import SCOPE, tracked
    t = {c["ticker"] for c in tracked()}
    return len(t - set(SCOPE)), f"of {len(t)} tracked companies are outside the proven set"


def _failure_types(files) -> tuple:
    from .failures import pareto
    p = pareto()
    return p["none"], f"of {p['total']} failure types"


def _interpretive(files) -> tuple:
    names = ("statements.csv", "projects.csv", "ai_spend.csv")
    return sum(len(_csv(files, n)) for n in names), "rows in " + ", ".join(n for n in names)


def _restated(files) -> tuple:
    rows = _csv(files, "values.csv")
    return sum(r.get("basis") == "restated" for r in rows), f"of {len(rows)} values in values.csv read restated"


def _asset_types(files) -> tuple:
    from .status import confirmed
    from .taxonomy import asset_types
    entries = [e for block in asset_types().values() if isinstance(block, dict) for e in block.values()]
    return sum(not confirmed(e) for e in entries), f"of {len(entries)} mappings have no confirmed_by"


COMPUTED = {"xbrl_off_systematic_escapes": lambda files: _escapes("systematic"), "omission_escapes": lambda files: _escapes("omission"),
            "values_agreeing_with_xbrl": _agree, "companies_outside_proven": _outside, "failure_types_without_check": _failure_types,
            "interpretive_rows": _interpretive, "restated_values": _restated, "asset_types_unconfirmed": _asset_types}


def resolved(files=None, entries=None) -> list[dict]:
    """The entries with `count` (int or None) and `of` (what the count counts) beside `rows`; `all` stays `all`."""
    out = []
    for e in load() if entries is None else entries:
        r = e["rows"]
        count, of = COMPUTED[r["computed"]](files) if isinstance(r, dict) else (None if r == "all" else r, "all rows" if r == "all" else "")
        out.append({**e, "count": count, "of": of})
    return out


def unmitigated(entries) -> list[dict]:
    """The entries whose mitigation is `none` (the checklist's informational line)."""
    return [e for e in entries if str(e["mitigation"]).strip().lower() == "none"]


def _cell(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def markdown(version: str, files=None, entries=None) -> str:
    """LIMITATIONS.md: intended use and not for use, the entries as a table, cadence, correction policy, support."""
    es = resolved(files, entries)
    rows = lambda e: "all" if e["rows"] == "all" else ("unknown" if e["count"] is None else str(e["count"])) + (f" {e['of']}" if e["of"] else "")
    return "\n".join([
        f"# Limitations of {version}", "",
        "## Intended use", "",
        "For research on the reported revenue, capex, opex and note figures of the companies in this release (the proven set), "
        "each traced to the cell of the 10-K it came from. Not for automated trading decisions. Not for companies outside the proven set "
        "without your own review. Not an estimate of AI spend: `ai_spend.csv`, `statements.csv` and `projects.csv` quote what companies said, "
        "and the ledger adds no estimate of its own.", "",
        "## Known weaknesses", "",
        f"{len(es)} entries from `taxonomy/limitations.yaml`; {len(unmitigated(es))} have no mitigation in place. "
        "Counts are computed from the data when the packet is built.", "",
        "| Id | Weakness | Affected | Mitigation | Would close it |", "|---|---|---|---|---|",
        *[f"| `{e['id']}` | {_cell(e['weakness'])} | {_cell(rows(e))} | {_cell(e['mitigation'])} | {_cell(e['closes'])} |" for e in es], "",
        "## Cadence", "",
        "Releases are built on demand, when new filings arrive or a decision changes a row; there is no fixed schedule.", "",
        "## Corrections", "",
        "A correction ships as a new release whose DIFF.md names every row that changed. A signed release is never edited.", "",
        "## Support", "",
        "The person who signed this release, named in SIGNOFF.json beside this file. No email address is published.", ""])
