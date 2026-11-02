"""The claims register (docs/BUILD.md): every claim the product makes, its status computed from facts where a fact can
decide it, and the review findings not yet fixed.

`claims/claims.yaml` declares each claim (what it says, where, what backs it, a declared status, its gaps). `computed`
checks every entry:

  - a row with `checks` starts from proven and the facts decide (a declared stale or stub is not a floor); a row
    without checks starts from its declared status and can only get worse;
  - every backed_by test must exist (tests/<module>.py, class, method; on the hosted copy, which ships no tests/, the
    presence recorded at deploy in claims/hosted.json), must not have been skipped or failed in the last recorded run
    (reports/tests.json `skipped_ids`, `failures`), and every backed_by function must import; a claim with no test, a
    listed gap or an open finding is never proven;
  - gold: 0 verdicts of N is a stub, some of N partial, a gold file that does not read a stub;
  - golden_report: reports/golden.json missing is stale, tables differing or a gold verdict failing a stub, gold
    unverified partial;
  - edgar_watch: data/watch.json older than 48 hours, or a time that is missing, unreadable, zone-less or in the future,
    is stale (clock.age_hours);
  - hosted_copy: no deploy record (claims/hosted.json) is stale; one from an older release, or (live) from code other
    than HEAD (a descendant that changed only claims/hosted.json is the same code), is stale. Never proven from silence;
  - mappings_confirmed: any asset-type mapping with no confirmed_by that the company's own tag does not check is partial.

live=False (docs/CLAIMS.md and every packet's LIMITATIONS.md, both hashed or diffed) leaves out the clock and HEAD:
what depends on them reads "checked live only", stale, so the same data gives the same text at any time on any commit.

`claims/findings.jsonl` is append-only: a finding changes state by a new line with the same id that changes only
`status` and `at`; every committed version of the file must be a prefix of the working one (`append_only`). The page
scan (`scan`) reads the label maps, badge and tone texts of every page and the card and cause texts of the Python that
feeds them; a string found with no register row, or a row's string no longer where it says, is a problem, and the
Release checklist's "Claims register" line is red while any exists, or when nothing was scanned.

`uv run python -m ledger claims` writes docs/CLAIMS.md; `--deployed` records the hosted copy's deploy (claims/hosted.json)
right after `railway up` (refused on a dirty tree)."""
from __future__ import annotations

import ast
import importlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import store
from .clock import age_hours

REPO = Path(__file__).resolve().parents[1]  # code-tracked things (the register, tests, pages, docs) always from the repo
FILE = REPO / "claims" / "claims.yaml"
FINDINGS = REPO / "claims" / "findings.jsonl"
FINDINGS_REL = "claims/findings.jsonl"
HOSTED = REPO / "claims" / "hosted.json"
PAGES = REPO / "ledger" / "pages"
PY = REPO / "ledger"
TESTS = REPO / "tests"
DOC = REPO / "docs" / "CLAIMS.md"
WATCH = store.ROOT / "data" / "watch.json"
GOLDEN_REPORT = store.ROOT / "reports" / "golden.json"
TEST_REPORT = store.ROOT / "reports" / "tests.json"
RELEASES = store.ROOT / "releases"

STATUSES = ("proven", "partial", "stale", "stub", "planned")  # best first: a computed status is the worst of these
RANK = {s: i for i, s in enumerate(STATUSES)}
PAGE_ORDER = {"stub": 0, "stale": 1, "partial": 2, "planned": 3, "proven": 4}  # the Gaps page: stub, stale, partial first
SEVERITIES = ("high", "medium", "low")
FINDING_STATES = ("open", "fixed", "wontfix")
REQUIRED = ("id", "claim", "where", "shown", "backed_by", "status", "gaps", "ticket")
FINDING_KEYS = ("id", "source", "severity", "text", "where", "claim", "ticket", "status", "at")
MUTABLE = ("status", "at")  # what a later line for the same finding may change
# Finding ids: branch-prefixed (F-RC7: F-, a code for the branch, a number) or S-<n> (state findings, ledger/states.py).
# Plain F<n> ids stop at LEGACY_MAX: two branches both took F14/F15 before this rule. claims/findings.jsonl merges by union
# (.gitattributes), so a reused id would otherwise land silently.
FINDING_ID = re.compile(r"^(F\d+|F-[A-Z]{2,}\d+|S-\d+)$")
LEGACY_MAX = 30
TICKET = re.compile(r"^(none|T\d+[a-z]?)$")
STALE_HOURS = 48


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── loading ──────────────────────────────────────────────────────────────────────────────────────────────────────
def load(path: Path = FILE) -> list[dict]:
    """The register in file order. ValueError on a missing field, a repeated id, an unknown status or check, checks on a
    planned row, a bad ticket, or a backed_by that is not {functions: [...], tests: [...]}."""
    raw = yaml.safe_load(path.read_text()) or []
    if not isinstance(raw, list):
        raise ValueError("claims: the register is a list of entries")
    out, seen = [], set()
    for n, e in enumerate(raw):
        if not isinstance(e, dict):
            raise ValueError(f"claims: entry {n} is not a mapping")
        missing = [k for k in REQUIRED if k not in e or e[k] is None]
        if missing:
            raise ValueError(f"claims: {e.get('id', n)} is missing {missing}")
        if e["id"] in seen:
            raise ValueError(f"claims: {e['id']} appears twice")
        seen.add(e["id"])
        if e["status"] not in STATUSES:
            raise ValueError(f"claims: {e['id']} has status {e['status']!r}; one of {STATUSES}")
        if not TICKET.match(str(e["ticket"])):
            raise ValueError(f"claims: {e['id']} ticket {e['ticket']!r}; a ticket id or none")
        b = e["backed_by"]
        if not (isinstance(b, dict) and set(b) == {"functions", "tests"} and all(isinstance(b[k], list) for k in b)):
            raise ValueError(f"claims: {e['id']} backed_by must be {{functions: [...], tests: [...]}}")
        checks = list(e.get("checks") or [])
        bad = [c for c in checks if c not in CHECKS]
        if bad:
            raise ValueError(f"claims: {e['id']} names unknown checks {bad}; one of {sorted(CHECKS)}")
        if checks and e["status"] == "planned":
            raise ValueError(f"claims: {e['id']} is planned and has checks; nothing built, nothing to check")
        for k in ("where", "shown", "gaps"):
            if not isinstance(e[k], list):
                raise ValueError(f"claims: {e['id']} {k} must be a list")
        out.append({**e, "checks": checks})
    return out


def findings(path: Path = FINDINGS, ids: set | None = None) -> list[dict]:
    """The findings log, latest line per id, in first-seen order. ValueError on a line that does not read, lacks a key,
    has an unknown severity or state, names a claim the register lacks (with `ids`), or, as a later line for a finding,
    changes anything but status and at."""
    if not path.exists():
        return []
    latest: dict = {}
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            f = json.loads(line)
        except ValueError as e:
            raise ValueError(f"findings: line {n} does not read ({e})") from None
        if not isinstance(f, dict):
            raise ValueError(f"findings: line {n} is not an object")
        missing = [k for k in FINDING_KEYS if k not in f]
        if missing:
            raise ValueError(f"findings: line {n} ({f.get('id')}) lacks {missing}")
        if f["severity"] not in SEVERITIES or f["status"] not in FINDING_STATES:
            raise ValueError(f"findings: {f['id']} severity {f['severity']!r} / status {f['status']!r}")
        if ids is not None and f["claim"] not in ids:
            raise ValueError(f"findings: {f['id']} names claim {f['claim']!r}, not in the register")
        if not TICKET.match(str(f["ticket"])):
            raise ValueError(f"findings: {f['id']} ticket {f['ticket']!r}")
        m = FINDING_ID.match(str(f["id"]))
        if not m or (str(f["id"])[1:].isdigit() and int(str(f["id"])[1:]) > LEGACY_MAX):
            raise ValueError(f"findings: line {n} id {f['id']!r}: a new finding takes a branch-prefixed id (F-<CODE><n>) or S-<n>")
        was = latest.get(f["id"])
        if was is None and f["status"] != "open":
            raise ValueError(f"findings: line {n} closes {f['id']}, which has no earlier open line")
        if was is not None and f["status"] == "open" and was["status"] == "open":
            raise ValueError(f"findings: line {n} opens {f['id']} again; the id is already taken (two branches chose it?)")
        if was is not None:
            changed = sorted(k for k in set(was) | set(f) if k not in MUTABLE and was.get(k) != f.get(k))
            if changed:
                raise ValueError(f"findings: line {n} changes {changed} of {f['id']}; a later line may change only {MUTABLE}, a new finding takes a new id")
        latest[f["id"]] = f
    return list(latest.values())


def open_findings(fs: list[dict] | None = None) -> list[dict]:
    fs = findings() if fs is None else fs
    return [f for f in fs if f["status"] == "open"]


def _git(*args, cwd: Path | None = None) -> subprocess.CompletedProcess | None:
    try:
        r = subprocess.run(["git", *args], cwd=cwd or REPO, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r


def append_only(path: Path = FINDINGS, rel: str = FINDINGS_REL, repo: Path | None = None) -> dict:
    """{enforced, commits, problems}: every committed version of the findings log must be a prefix of the working file.
    Without git (the hosted copy) nothing can be compared: enforced False, said so, never a silent pass."""
    log = _git("log", "--first-parent", "--format=%H", "--", rel, cwd=repo)
    if log is None or log.returncode != 0:
        return {"enforced": False, "commits": 0, "problems": [], "note": "append-only not enforced here: no git"}
    now = path.read_text() if path.exists() else ""
    shas = [s for s in log.stdout.split() if s]
    problems = []
    for sha in shas:
        old = _git("show", f"{sha}:{rel}", cwd=repo)
        if old is None or old.returncode != 0:
            continue  # the commit that deleted it, or a rename: nothing to compare
        if not now.startswith(old.stdout):
            problems.append(f"{sha[:7]}: a line was edited or removed; append a new line with the same id instead")
    return {"enforced": True, "commits": len(shas), "problems": problems,
            "note": f"append-only checked against {len(shas)} commits" if not problems else f"{len(problems)} commits are not a prefix"}


# ── what backs a claim ───────────────────────────────────────────────────────────────────────────────────────────
def _hosted_record() -> dict | None:
    try:
        h = json.loads(HOSTED.read_text())
        return h if isinstance(h, dict) else None
    except (OSError, ValueError):
        return None


def test_exists(tid: str, tests_dir: Path | None = None) -> bool:
    """tests.<module>.<Class>.<method> names a method in that file, read as source (nothing is imported). Without a
    tests/ folder (the hosted copy) the presence recorded at deploy time answers, and an unrecorded id is absent."""
    tests_dir = tests_dir or TESTS
    parts = tid.split(".")
    if len(parts) != 4 or parts[0] != "tests":
        return False
    if not tests_dir.is_dir():
        return bool(((_hosted_record() or {}).get("tests") or {}).get(tid))
    f = tests_dir / f"{parts[1]}.py"
    if not f.is_file():
        return False
    try:
        tree = ast.parse(f.read_text())
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == parts[2]:
            return any(isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == parts[3] for m in node.body)
    return False


def function_imports(name: str) -> str | None:
    """None when ledger.<module>.<attr>[.<attr>] imports and resolves, else why not (any exception a module raises at
    import is a reason, never a crash)."""
    parts = name.split(".")
    last = "no module"
    for i in range(len(parts) - 1, 0, -1):
        try:
            obj = importlib.import_module(".".join(parts[:i]))
        except ModuleNotFoundError as e:
            last = f"no module ({e.name})"
            continue
        except Exception as e:  # a module that raises at import: a reason
            return f"{'.'.join(parts[:i])} raises at import: {e.__class__.__name__}: {str(e)[:100]}"
        try:
            for a in parts[i:]:
                obj = getattr(obj, a)
            return None
        except AttributeError:
            return f"{'.'.join(parts[:i])} has no {'.'.join(parts[i:])}"
    return last


def test_run(path: Path | None = None) -> dict:
    """The last recorded run (reports/tests.json): {recorded, skipped, failed, at}. recorded False when there is no
    report, or it predates `skipped_ids`: a skip cannot be told from a pass, so the claim is not proven on it."""
    try:
        t = json.loads((path or TEST_REPORT).read_text())
    except (OSError, ValueError):
        return {"recorded": False, "skipped": set(), "failed": set(), "at": None}
    failed = {str(l).split(":", 1)[0].strip() for l in t.get("failures") or []}
    return {"recorded": "skipped_ids" in t, "skipped": set(t.get("skipped_ids") or []), "failed": failed, "at": t.get("at")}


# ── the checks: each (ctx) -> list of (status, phrase, detail); phrase is stable, detail carries the facts ───────────
def _gold(ctx) -> list:
    from . import gold
    from .config import PROVEN
    docs, problems = gold.load_checked(gold.GOLD, expect=list(PROVEN))
    if problems:
        return [("stub", "gold set does not read", "; ".join(problems)[:300])]
    items = [i for d in docs.values() for i in d["items"]]
    k = sum(gold.has_verdict(i) for i in items)
    if not items or k == 0:
        return [("stub", "no gold verdicts", f"0 of {len(items)} gold items have a verdict")]
    if k < len(items):
        return [("partial", "gold verdicts incomplete", f"{k} of {len(items)} gold items have a verdict")]
    return []


def _edgar(ctx) -> list:
    if not ctx["live"]:
        return [("stale", "EDGAR freshness checked live only", "the EDGAR check's age depends on the clock; see the Gaps page")]
    try:
        w = json.loads(WATCH.read_text())
    except (OSError, ValueError):
        return [("stale", "EDGAR never checked", "no EDGAR check on file")]
    hours, problem = age_hours((w or {}).get("checked_at"), ctx["now"])
    if problem:
        return [("stale", f"EDGAR check time {problem}", f"EDGAR check time {problem}: {(w or {}).get('checked_at')}")]
    if hours > STALE_HOURS:
        return [("stale", f"EDGAR check older than {STALE_HOURS} h", f"EDGAR last checked {str(w['checked_at'])[:10]}, {hours / 24:.1f} days ago")]
    return []


def latest_signed() -> str | None:
    from .release import version_key
    vs = [p.name for p in RELEASES.glob("v*") if p.is_dir() and (p / "SIGNOFF.json").exists()] if RELEASES.exists() else []
    return max(vs, key=version_key) if vs else None


def _same_code(recorded: str | None, head: str | None) -> bool:
    """HEAD is the recorded commit, or a descendant whose only change since is claims/hosted.json (the commit that recorded
    the deploy), as checklist.tests_line forgives the commit that records a test run."""
    if not recorded or not head:
        return False
    if recorded == head or head.startswith(recorded) or recorded.startswith(head):
        return True
    from .testreport import changed_since
    ch = changed_since(recorded, REPO)
    return ch is not None and all(p == "claims/hosted.json" for p in ch)


def _hosted(ctx) -> list:
    h = _hosted_record()
    if h is None:
        return [("stale", "hosted deploy not recorded", "No deploy record: the data and code the hosted copy serves are unknown")]
    out = []
    last = latest_signed()
    if h.get("release") != last:
        out.append(("stale", "hosted copy serves an older release", f"Hosted copy serves {h.get('release')}; latest signed release is {last}"))
    if not ctx["live"]:
        out.append(("stale", "hosted code checked live only", "Whether the hosted copy runs this code depends on HEAD; see the Gaps page"))
    elif not _same_code(h.get("commit"), _head()):
        out.append(("stale", "hosted copy runs other code", f"Hosted copy deployed from {h.get('commit')} on {str(h.get('deployed_at'))[:10]}; this checkout is at {_head() or 'an unknown commit (no git)'}"))
    return out


def _mappings(ctx) -> list:
    """Asset-type mappings neither a person confirmed nor the company's own tag checks: filertag.tally, the one count
    every packet's limitations line reads too. When the company tags could not be read, nothing counts as verified and
    the detail says so (never "0 verified")."""
    from .filertag import tally
    c = tally()
    if not c["waiting"]:
        return []
    how = f"; {c['verified']} match the company's own tag" if c["read"] else "; company tags not read"
    return [("partial", "category mappings unconfirmed", f"{c['waiting']} of {c['entries']} category mappings await a person's confirmation{how}")]


def _golden(ctx) -> list:
    try:
        g = json.loads(GOLDEN_REPORT.read_text())
    except (OSError, ValueError):
        return [("stale", "golden not run", "No golden run on file")]
    out = []
    tables = g.get("tables_ok", g.get("ok")) and not g.get("failed_step")
    if not tables:
        out.append(("stub", "golden differs", f"Golden failed at {g.get('failed_step')}" if g.get("failed_step") else "Golden tables differ from the expectation"))
    gd = g.get("gold") or {}
    state = gd.get("state")
    if state == "fail":
        out.append(("stub", "gold verdicts fail", f"{len(gd.get('failures') or [])} gold verdicts no longer hold"))
    elif state != "pass":
        out.append(("partial", "gold unverified", f"Gold unverified: {gd.get('unverified')} of {gd.get('items')} items have no verdict" if state else "Golden report has no gold state"))
    return out


CHECKS = {"gold": _gold, "edgar_watch": _edgar, "hosted_copy": _hosted, "mappings_confirmed": _mappings, "golden_report": _golden}


def _head() -> str | None:
    from .testreport import git_state
    return git_state(REPO)[0]


def worst(*statuses: str) -> str:
    return max(statuses, key=lambda s: RANK[s])


def compute(entry: dict, ctx: dict, open_by_claim: dict, run: dict) -> dict:
    """One entry with `declared`, the computed `status`, `reasons` [{status, phrase, detail}], `facts` (the gaps the
    checks found, in words), `open_findings` and `worse`."""
    reasons, facts = [], []
    if entry["status"] != "planned":
        tests = entry["backed_by"]["tests"]
        if not tests:
            reasons.append(("partial", "no test backs it", ""))
        for t in tests:
            if not test_exists(t):
                reasons.append(("partial", "a backing test does not exist", t))
            elif t in run["failed"]:
                reasons.append(("stub", "a backing test failed", t))
            elif t in run["skipped"]:
                reasons.append(("partial", "a backing test was skipped", t))
        if tests and not run["recorded"]:
            reasons.append(("partial", "backing tests' last run not recorded", "reports/tests.json has no skipped_ids: run `ledger test`"))
        for fn in entry["backed_by"]["functions"]:
            why = function_imports(fn)
            if why:
                reasons.append(("partial", "a backing function does not import", f"{fn}: {why}"))
        if entry["gaps"]:
            reasons.append(("partial", "gaps listed", f"{len(entry['gaps'])} listed"))
        n = len(open_by_claim.get(entry["id"], []))
        if n:
            reasons.append(("partial", "open findings", f"{n} open"))
        for c in entry["checks"]:
            try:
                got = CHECKS[c](ctx)
            except Exception as e:  # a check that cannot run never reads as a pass
                got = [("stale", f"check {c} could not run", f"{e.__class__.__name__}: {str(e)[:120]}")]
            reasons.extend(got)
            facts.extend(d for _, _, d in got if d)
    base = "proven" if entry["checks"] else entry["status"]  # with checks, the facts decide; without, the declaration is the ceiling
    status = worst(base, *(r[0] for r in reasons))
    return {**entry, "declared": entry["status"], "status": status, "worse": RANK[status] > RANK[entry["status"]],
            "better": RANK[status] < RANK[entry["status"]], "facts": facts,
            "reasons": [{"status": s, "phrase": p, "detail": d} for s, p, d in reasons],
            "open_findings": [f["id"] for f in open_by_claim.get(entry["id"], [])]}


def computed(live: bool = True, now: datetime | None = None, entries: list[dict] | None = None, fs: list[dict] | None = None,
             run: dict | None = None) -> list[dict]:
    """Every claim with its computed status. live=False leaves out what depends on the clock or on HEAD."""
    es = load() if entries is None else entries
    fs = findings(ids={e["id"] for e in es}) if fs is None else fs
    by: dict = {}
    for f in open_findings(fs):
        by.setdefault(f["claim"], []).append(f)
    ctx = {"live": live, "now": now or _now()}
    run = test_run() if run is None else run
    return [compute(e, ctx, by, run) for e in es]


def counts(rows: list[dict], fs: list[dict]) -> dict:
    out = {s: sum(r["status"] == s for r in rows) for s in STATUSES}
    out["open_findings"] = len(open_findings(fs))
    return out


def counts_line(c: dict) -> str:
    return " · ".join(f"{s} {c[s]}" for s in STATUSES) + f" · open findings {c['open_findings']}"


# ── the page scan ────────────────────────────────────────────────────────────────────────────────────────────────
# Label maps whose display strings are claims (value strings, or the keys when every value is a CSS class).
LABEL_MAPS = {"trail.js": ("TRAIL_TONE",), "reconcile.js": ("STATE_BADGE",), "release.js": ("LINE_STATE",), "_shared.js": ("CHECK", "CROP_STATE"),
              "proof.js": ("GOLD_WORD",)}
# The text of an element styled as a status (a badge or a tone colour), literal or the static parts of a template.
TONED = re.compile(r"""h\('[a-z0-9]+',\s*\{[^{}]*class:\s*'[^']*(?:badge|text-(?:green|red|orange|teal|azure|yellow))[^']*'[^{}]*\},\s*('[^']*'|`[^`]*`)""")
# Strings a page shows that the two rules above cannot see (a class picked at run time, a heading).
WATCHED = ("'Proven'", "Ready for release", "Not in scope", "Next 10-K expected", "Tables unchanged", "Tables changed", "Hand check: ", "'Hand check'",
           "No items to review", "Quotes verified", "95% CI", "Planted errors", "Matches SEC XBRL", "Read-only", "Make this a rule", "Make this a definition",
           "`Sign ${cl.version}`", "'Known gaps'", "Compare filings", "Open in filing")
# The Python that feeds the pages: the cards' sentences and Reconcile's cause labels.
PY_RULES = {"cards.py": (re.compile(r'(?:"text":\s*|\btext = )f?"([^"{]*)'),),
            "mapcard.py": (re.compile(r'(?:\breturn |"text":\s*)f?"([^"{]*)'),),
            "workbench.py": (re.compile(r'CAUSES = \{(.*?)\}\n', re.S), re.compile(r'FINDING_LABEL = \{(.*?)\}\n', re.S), re.compile(r'"cause_label": \{([^}]*)\}'))}
CSS = re.compile(r"^(bg|text|fw|ms|me|mt|mb)-")
GAPS_OWN = frozenset(STATUSES) | {"high", "medium", "low"}  # the Gaps page's own chips: the register's vocabulary, not claims


def _fragments(lit: str) -> list[str]:
    parts = re.split(r"\$\{[^}]*\}", lit[1:-1]) if lit[0] == "`" else [lit[1:-1]]
    out = []
    for p in parts:
        p = p.strip(" ,·:—()●")
        if len(re.findall("[A-Za-z]", p)) >= 3:
            out.append(p)
    return out


def _map_strings(body: str) -> list[str]:
    quoted = re.findall(r"'([^']*)'", body)
    vals = [q for q in quoted if not CSS.match(q)]
    keys = re.findall(r"(?:^|[{,])\s*'?([A-Za-z_][A-Za-z_ ]*)'?\s*:", body)
    if not [v for v in vals if v not in keys]:  # every value is a class: the keys are what the page shows
        return keys
    return [v for v in vals if v not in keys]


def strings_in(name: str, text: str) -> set[str]:
    """The claim strings one file shows, by the rules for its kind."""
    found = set()
    if name.endswith(".js") or name.endswith(".html"):
        found |= {w for w in WATCHED if w in text}
        for m in LABEL_MAPS.get(name, ()):
            hit = re.search(r"const " + m + r" = \{(.*?)\};", text, re.S)
            if hit:
                found |= set(_map_strings(hit.group(1)))
        for lit in TONED.findall(text):
            found |= set(_fragments(lit))
    for rx in PY_RULES.get(name, ()):
        for blk in rx.findall(text):
            vals = re.findall(r':\s*"([^"]*)"', blk) if ":" in blk and '"' in blk else [blk]
            found |= {v.strip(" ,·:") for v in vals if len(v.strip(" ,·:")) >= 3}
    if name == "gaps.js":
        found -= GAPS_OWN
    return found


def scan(pages: Path | None = None, py: Path | None = None, html: Path | None = None) -> dict:
    """{files, pages, strings: {string: [files]}}: every page script, app.html, and the Python with rules."""
    pages, py = pages or PAGES, py or PY
    html = html if html is not None else PY / "app.html"
    files = sorted(pages.glob("*.js")) + ([html] if html.is_file() else []) + sorted(p for p in py.glob("*.py") if p.name in PY_RULES)
    strings: dict = {}
    for f in files:
        for s in strings_in(f.name, f.read_text()):
            strings.setdefault(s, []).append(f.name)
    return {"files": len(files), "pages": sum(f.suffix == ".js" for f in files), "strings": strings}


def unregistered(entries: list[dict] | None = None, pages: Path | None = None, repo: Path = REPO, py: Path | None = None, html: Path | None = None) -> list[dict]:
    """[{kind, what, where}]: a scanned string no row lists in `shown` (unregistered), a row's shown string found in none
    of the files its `where` names (not_shown), a ledger/ path in `where` that does not exist (missing_file), a built row
    with nothing to look for (no_marker), or a scan that read no page or found no string (nothing_scanned)."""
    es = load() if entries is None else entries
    shown = {s for e in es for s in e["shown"]}
    sc = scan(pages, py, html)
    out = []
    if not sc["pages"] or not sc["strings"]:
        out.append({"kind": "nothing_scanned", "what": f"{sc['pages']} pages, {len(sc['strings'])} strings", "where": str(pages or PAGES)})
    for s, files in sorted(sc["strings"].items()):
        if s not in shown:
            out.append({"kind": "unregistered", "what": s, "where": ", ".join(sorted(set(files)))})
    for e in es:
        files = [repo / w for w in e["where"] if w.startswith("ledger/")]
        for w in e["where"]:
            if w.startswith("ledger/") and not (repo / w).exists():
                out.append({"kind": "missing_file", "what": w, "where": e["id"]})
        if e["status"] != "planned" and not e["shown"]:
            out.append({"kind": "no_marker", "what": "shown is empty: name a string in one of its files", "where": e["id"]})
        texts = [p.read_text() for p in files if p.is_file()]
        for s in e["shown"]:
            if not any(s in t for t in texts):
                out.append({"kind": "not_shown", "what": s, "where": e["id"]})
    return out


# ── outputs ──────────────────────────────────────────────────────────────────────────────────────────────────────
def payload(live: bool = True) -> dict:
    """/api/v1/claims: counts, every claim (page order), the open findings, the scan and the append-only check."""
    es = load()
    fs = findings(ids={e["id"] for e in es})
    rows = sorted(computed(live, entries=es, fs=fs), key=lambda r: PAGE_ORDER[r["status"]])
    sc = scan()
    return {"at": _now().isoformat(timespec="seconds"), "live": live, "counts": counts(rows, fs), "claims": rows,
            "findings": open_findings(fs), "problems": unregistered(es), "scanned": {"files": sc["files"], "pages": sc["pages"], "strings": len(sc["strings"])},
            "append_only": append_only()}


def _cell(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def markdown() -> str:
    """docs/CLAIMS.md: the static view (no clock, no HEAD), so it changes only when the register, the findings, the
    last test run's skips, the gold files, the golden report, the mappings or the signed releases change."""
    es = load()
    fs = findings(ids={e["id"] for e in es})
    rows = sorted(computed(False, entries=es, fs=fs), key=lambda r: (PAGE_ORDER[r["status"]], r["id"]))
    c = counts(rows, fs)
    lines = ["# Claims register", "",
             "Generated by `uv run python -m ledger claims` from `claims/claims.yaml` and `claims/findings.jsonl`; do not edit by hand. "
             "A row with checks gets its status from the facts; a row without checks starts from its declared status and only gets worse. "
             "This file leaves out what depends on the clock or the commit (the EDGAR check's age, the code the hosted copy runs): those read "
             "\"checked live only\" here; the Gaps page and `/api/v1/claims` check them live. How to add a claim or a finding: docs/BUILD.md.", "",
             counts_line(c), "",
             "| Claim | Where | Declared | Computed | Why | Gaps | Ticket |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        why = "; ".join(x["phrase"] for x in r["reasons"] if x["phrase"] != "gaps listed")
        gaps = r["gaps"] + r["facts"]
        lines.append(f"| {_cell(r['claim'])} (`{r['id']}`) | {_cell(', '.join(r['where']))} | {r['declared']} | **{r['status']}** | {_cell(why) or '—'} | "
                     f"{_cell('; '.join(gaps)) or '—'} | {r['ticket']} |")
    lines += ["", "## Open findings", "", "| Id | Severity | Finding | Where | Claim | Ticket | Source | Since |", "|---|---|---|---|---|---|---|---|"]
    for f in sorted(open_findings(fs), key=lambda f: (SEVERITIES.index(f["severity"]), f["id"])):
        lines.append(f"| {f['id']} | {f['severity']} | {_cell(f['text'])} | {_cell(f['where'])} | `{f['claim']}` | {f['ticket']} | {_cell(f['source'])} | {f['at']} |")
    return "\n".join(lines) + "\n"


def packet_section() -> list[str]:
    """LIMITATIONS.md's claims section: the stub, stale and planned claims, static (live=False): the packet is hashed,
    so its text depends on the data and the register, never on the clock or HEAD. A register or check that fails
    reads as such in the packet, never as a crash."""
    try:
        rows = computed(False)
    except Exception as e:
        return ["## Claims not yet proven", "", f"The claims register could not be read when the packet was built ({e.__class__.__name__}): every claim is unverified.", ""]
    bad = sorted((r for r in rows if r["status"] in ("stub", "stale", "planned")), key=lambda r: (PAGE_ORDER[r["status"]], r["id"]))
    out = ["## Claims not yet proven", "",
           f"{len(bad)} claims of {len(rows)} in the claims register (claims/claims.yaml) are stub, stale or planned, computed from the data when the packet is built. "
           "Freshness that depends on the clock (the EDGAR check, the hosted copy) reads \"checked live only\" here.", "",
           "| Claim | Status | Why | Would close it |", "|---|---|---|---|"]
    for r in bad:
        why = sorted({x["phrase"] for x in r["reasons"] if RANK[x["status"]] >= RANK["stale"]}) or r["gaps"][:1]
        out.append(f"| {_cell(r['claim'])} | {r['status']} | {_cell('; '.join(why))} | {r['ticket']} |")
    return out + [""]


def record_deploy(release: str | None = None) -> dict:
    """claims/hosted.json: what the hosted copy was deployed from, and which backing tests exist (the image ships no
    tests/, so the hosted Gaps page reads their presence from here). Run right after `railway up`; refused on a dirty
    tree or without git, since the deploy uploads the working tree and a commit would not name it."""
    from .testreport import git_state
    sha, dirty = git_state(REPO)
    if not sha or dirty is None:
        raise ValueError("no git here: a deploy record needs the commit the hosted copy was built from")
    if dirty:
        raise ValueError("the tree is dirty: commit first, then deploy and record, so the record names the code that was uploaded")
    tests = sorted({t for e in load() for t in e["backed_by"]["tests"]})
    d = {"deployed_at": _now().isoformat(timespec="seconds"), "release": release or latest_signed(), "commit": sha,
         "tests": {t: test_exists(t) for t in tests}}
    HOSTED.write_text(json.dumps(d, indent=1) + "\n")
    return d


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--deployed" in argv:
        try:
            print(json.dumps(record_deploy(), indent=1))
        except ValueError as e:
            print(f"not recorded: {e}")
            return 1
        return 0
    text = markdown()
    if "--check" in argv:
        ok = DOC.exists() and DOC.read_text() == text
        print("docs/CLAIMS.md is current" if ok else "docs/CLAIMS.md is stale: run uv run python -m ledger claims")
        return 0 if ok else 1
    DOC.write_text(text)
    rows = computed(True)
    sc = scan()
    print(f"wrote {DOC.relative_to(REPO)}; live: {counts_line(counts(rows, findings()))}; scanned {sc['files']} files, {len(sc['strings'])} strings")
    for p in unregistered():
        print(f"  {p['kind']}: {p['what']} ({p['where']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
