"""The Docs section of Kenny's Data Emporium: the repository's own docs/*.md, served read-only, plus two pages written
from code on every request so they cannot drift from it (the glossary, from ledger/core/states.py and the terms below;
rules and checks, from rules/*.yaml, the answer keys and the release gates).

Only a top-level file in docs/ whose name is `[A-Za-z0-9_-]+.md` is ever read: no other suffix, no subfolder (docs/archive
is not served), no path traversal. `read` is the one function that opens a file."""
from __future__ import annotations

import re
from pathlib import Path

from ..core import store

DOCS = store.ROOT / "docs"
NAME = re.compile(r"^[A-Za-z0-9_-]+\.md$")

# The sidebar, in order: (slug, title, file in docs/ or None for a page written from code). A doc that is stale or
# superseded is left off the sidebar rather than shown; it stays readable at /docs/<NAME>.md.
SIDEBAR = (
    ("overview", "How it works", "OVERVIEW.md"),
    ("operations", "Operating guide", "OPERATIONS.md"),
    ("glossary", "Glossary", None),
    ("map", "Map", "MAP.md"),
    ("states", "States", "STATES.md"),
    ("rules", "Rules and checks", None),
    ("evals", "Evaluation", "EVALS.md"),
    ("claims", "Known limitations", "CLAIMS.md"),
    ("handoff", "Handoff", "HANDOFF.md"),
)
SLUGS = {s for s, _, _ in SIDEBAR}

# The app's pages, as the top navigation names them (ledger/web/app.html): the routes a doc may link to as #<page>.
APP_PAGES = {"proof": "Proof", "rules": "Rules", "reconcile": "Reconcile", "data": "Dataset", "explore": "Explore",
             "release": "Release", "gaps": "Known gaps", "docs": "Docs"}

# Words a page shows that are not state words, defined once. The state words come from ledger/core/states.py.
TERMS = (
    ("10-K", "A company's annual report filed with the SEC. The pipeline's primary source; 10-K/A amendments are read as their original's lineage."),
    ("Answer key", "An independent record a figure is compared with (`status.ANSWER_KEYS`): a twin, a second source, a tie, a later truth or a second reading. Ranked by independence in `status.KEY_GRADE`."),
    ("Twin", "The filer's own machine-readable value for the same concept and period (SEC XBRL, or ESEF). The strongest answer key. A match reads Verified."),
    ("Tie", "Parts that sum to a total the same filing tags in XBRL, within (n + 1) × half the coarsest rounding unit. Proves the sum, never one part. A tie reads Corroborated."),
    ("Second reading", "The same figure printed by two or more of the filer's 10-Ks (the comparative column of the next year). Rules out a one-off misread; shares the filer's pedigree. Reads Corroborated."),
    ("Second source", "The same figure in another document by the same filer (an 8-K earnings release against the 10-K). Declared in code; no row carries it yet."),
    ("Later truth", "A period's actual against what the company planned for it. Declared in code; no row carries it yet."),
    ("Company tag", "The company's own XBRL member on a reported PP&E category, matching the proposed us-gaap member. Reads Matches company tag."),
    ("Citation", "The table, row, column and cell an agent names for every number it returns. `extract --load` rejects a value whose cell does not exist or does not equal the value."),
    ("Citation only", "A figure with no answer key: untagged, no tie, one reading. It reads Unverified; the citation is the only evidence."),
    ("Crop", "A picture of the cited cell on the rendered 10-K: the row, two rows either side and the column header, the cell boxed (`ledger/checks/crops.py`)."),
    ("XBRL", "The tagged data a US filer submits with each filing. The pipeline's free answer key; the reader never sees it while reading."),
    ("ESEF", "The European tagged-filing format. A twin for European filers; tested in a spike, not in production."),
    ("EDGAR", "The SEC's filing system. `ledger watch` asks it for 10-Ks the ledger has not read."),
    ("Task fingerprint", "The SHA-256 of an agent task (`_run.task_sha`). An output loads only when it answered the current task; an older answer is refused as stale."),
    ("Prompt version", "`<agent>@v<n>` in `agents/prompts/`. A prompt is never edited in place; a change is the next version, switched on as a second step."),
    ("Charter", "`agents/charters/<id>.md`: what an agent owns, what it never touches, its input and output files, model, tools, prompt versions and the checks that judge it."),
    ("Rule", "A check in `rules/*.yaml` with an id, severity (block, warn, info), description, rationale and owner. `ledger rules` writes its exceptions."),
    ("Guard", "A check in code that tags a part-year or program statement (`ledger/checks/guards.py`) so it explains rather than misleads."),
    ("Exception", "One firing of a rule on one row, in the `exceptions` table."),
    ("Definition", "A judgement made once per company and applied on every run (`definitions/companies.yaml`): who, why, and for revenue and opex the periods it covers."),
    ("Resolution", "A person's decision on a queue item (accept, explain, fix, blocks), keyed to the item's content in `decisions/resolutions.jsonl`. It holds only while the item is unchanged."),
    ("Checked", "Agrees with an independent check: an answer key, a verified quote, a located table, or a confirmed mapping."),
    ("Explained", "Does not match, and a record on file says why by name: a definition, an info rule, a guard, a label with XBRL looked up and empty, or a person's resolution."),
    ("Open", "Neither checked nor explained. The only rows a person looks at. Blocked rows count as open too."),
    ("Proven set", "The companies every number is proven on before the set widens (`config.PROVEN`). The release scope is `config.SCOPE`."),
    ("Golden test", "`ledger golden --check`: rebuilds the proven set from frozen inputs in `fixtures/` and compares every table. A regression test: equal tables do not mean correct tables."),
    ("Gold set", "A stratified sample of values and facts per proven company (`gold/<TICKER>.json`) that a person checks against the filing: Right, Wrong or Can't say. The error rate is wrong of (right + wrong) with a Wilson 95% interval."),
    ("Hand check", "The gold set as the Proof page shows it: 20 items per proven company, each with its verdict. Unchecked never passes."),
    ("Wilson interval", "The 95% confidence interval for a share k of n (`ledger/core/stats.py`). Every estimated share is shown with its n and this interval."),
    ("Planted fault", "A real extraction corrupted one way at a time (wrong column, stale column, wrong row, scale, sign, digits, omission) to measure what catches it (`ledger faults`)."),
    ("Gate", "A per-company release condition (`ledger/release/release.py` GATES): G1 every filing read, G4 every block decided, G5 every value confirmed on the filing, G6 no proposal left to confirm."),
    ("Release", "A versioned folder `releases/vX.Y.Z/` of CSVs and reports whose content hash a person signs. Same inputs, same hash."),
    ("Packet", "The files of a release: the lists as CSV, README.md, QUALITY.md, DIFF.md and LIMITATIONS.md, with manifest.json naming the prompt, parser, model and rule hashes."),
    ("Signoff", "`SIGNOFF.json`: who signed which hash, when, and the Release checklist as it stood. The one human act; agents never sign."),
    ("Claim", "A statement the product makes on a page, in the API or in a release, registered in `claims/claims.yaml` with what backs it and a computed status."),
    ("Finding", "An open review finding in `claims/findings.jsonl`, append-only, linked to a claim. It caps that claim at partial."),
    ("Taxonomy row", "One row shape for spent, committed, derived, planned and company-stated AI figures, every category a named standard's concept (`ledger/release/taxonomy.py`)."),
    ("Mapping", "A reported PP&E category mapped to a us-gaap member with the note's words as evidence (`taxonomy/asset_types.yaml`). A proposal until a person confirms it."),
    ("Proof", "The page that shows every row's state per stage per company, and whether each company is proven."),
    ("Rules", "The page that lists every rule, its findings, the agents and their scores."),
    ("Reconcile", "The review queue: open items with their evidence, and the actions that resolve them."),
    ("Dataset", "The released lists per company, with CSV export."),
    ("Explore", "Saved views and charts over the lists."),
    ("Release", "The page with the release checklist, the packet and the Sign button."),
    ("Known gaps", "The claims register and the open findings, with computed statuses."),
    ("Docs", "This section: the repository's documentation, read-only."),
    ("Company trail", "One company's rows through every step, each with what was found, where, and how it is known."),
)


def read(name: str, root: Path | None = None) -> str | None:
    """The text of docs/<name>, or None: a name that is not `[A-Za-z0-9_-]+.md`, a path outside docs/, or no such file."""
    base = Path(root or DOCS)
    if not isinstance(name, str) or not NAME.match(name):
        return None
    f = (base / name).resolve()
    if f.parent != base.resolve() or f.suffix != ".md" or not f.is_file():
        return None
    return f.read_text(encoding="utf-8")


def _cell(s) -> str:
    return " ".join(str(s).split()).replace("|", "\\|")


def glossary() -> str:
    """Every word a page shows for a state (ledger/core/states.py), then the key terms. Written on every request."""
    from ..core import states
    out = ["# Glossary", "",
           "Written from code on every request: the state words from `ledger/core/states.py`, the terms from `ledger/web/docs.py`. "
           "A state word belongs to exactly one state machine (or names one group of its states); [States](STATES.md) describes each machine.", "",
           "## State words", "", "| Word | Machine | State | Kind | Meaning |", "|---|---|---|---|---|"]
    for mid, m in states.MACHINES.items():
        for s in m.states:
            r = states.resolve(mid, s.name)
            out.append(f"| {_cell(r.label)} | {mid} ({m.doc}) | `{s.name}` | {s.kind} | {_cell(s.meaning) or '—'} |")
        for g, (w, members) in m.groups.items():
            out.append(f"| {_cell(w)} | {mid} ({m.doc}) | group `{g}` | group | {_cell(', '.join(members))} |")
    out += ["", "Kinds: good, neutral and open are ordinary; unknown, stale and missing are never good (not looked up, out of date, gone)."]
    out += ["", "## Terms", "", "| Term | Meaning |", "|---|---|"]
    out += [f"| {_cell(t)} | {_cell(d)} |" for t, d in TERMS]
    return "\n".join(out) + "\n"


def rules_page() -> str:
    """The rules in rules/*.yaml, the answer keys in strength order, and the release gates. Written on every request."""
    from ..checks.rules import load
    from ..core import status
    from ..release.release import GATES
    rules = load()
    sev = {s: [r for r in rules if r["severity"] == s] for s in ("block", "warn", "info")}
    out = ["# Rules and checks", "",
           "Written from code on every request: `rules/*.yaml`, `ledger/core/status.py` (answer keys) and `ledger/release/release.py` (gates). "
           "Every check is deterministic code; no model grades another model.", "",
           "## Order of checks", "",
           "1. The task hides the answer key: the reader sees the statement tables, never an XBRL value or tag (`ledger/extract/extract.py`).",
           "2. Shape: the answer must match its JSON schema (`agents/schemas/`); one retry with the reason, then a logged failure.",
           "3. Citation: every value's cell must exist in the parsed filing and equal the value (`citation_resolves`).",
           "4. Rules: " + ", ".join(f"{len(v)} {k}" for k, v in sev.items()) + f" ({len(rules)} in `rules/`).",
           "5. Answer keys: the strongest key that agrees decides the row's word (below).",
           "6. A second read on the rendered 10-K: the cited cell located by row label and column header, cropped and boxed (`ledger/checks/crops.py`).", "",
           "## Answer keys, strongest first", "", "| Key | `by` prefixes | Why it ranks here |", "|---|---|---|"]
    for k in status.KEY_GRADE:
        out.append(f"| {status.KEY_LABEL[k]} | {', '.join('`' + p + '`' for p in status.ANSWER_KEYS[k])} | {_cell(status.KEY_WHY[k])} |")
    out += ["", "## Rules", "", "Block refuses the release until decided; warn opens the rows it fires on; info explains.", "",
            "| Rule | Severity | Check | What it checks | Why |", "|---|---|---|---|---|"]
    for s in ("block", "warn", "info"):
        for r in sev[s]:
            out.append(f"| `{r['id']}` | {s} | `{r['check']}` | {_cell(r['description'])} | {_cell(r['rationale'])} |")
    out += ["", "## Release gates", "", "Per company, on the release scope. Any failing row refuses the release.", "", "| Gate | Condition |", "|---|---|"]
    out += [f"| {g} | {_cell(t)} |" for g, t in GATES.items()]
    return "\n".join(out) + "\n"


def index() -> dict:
    return {"pages": [{"slug": s, "title": t, "file": f or None, "generated": f is None} for s, t, f in SIDEBAR],
            "files": {f: s for s, _, f in SIDEBAR if f}, "app_pages": APP_PAGES}


def page(slug: str) -> dict | None:
    """{slug, title, file, markdown} for a sidebar page, or None."""
    for s, t, f in SIDEBAR:
        if s == slug:
            text = (glossary() if s == "glossary" else rules_page()) if f is None else read(f)
            if text is None:
                return None
            return {"slug": s, "title": t, "file": f"docs/{f}" if f else None, "markdown": text}
    return None
