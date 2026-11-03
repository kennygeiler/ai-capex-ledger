"""The Release page's checklist (T5) and the one act that signs from it (T6, docs/PROOF.md).

Every line is what could make a signature wrong, with its count and the page that fixes it: the gates per company
(release.gates), open and blocked items in the scope (proof.board, the one definition of open), answer-key values missing
from the dataset (proof.missing_from_dataset, T81: an XBRL value with no released value and nothing open), the decisions a run
left to confirm (resolutions.unconfirmed), unmapped asset types (taxonomy.unmapped), rows with no value by measure,
the diff in rows from the previous release (release.rows_diff), the limitations with no mitigation
(taxonomy/limitations.yaml, T68), the golden test and the last test run
(reports/golden.json, reports/tests.json), and the packet as `ledger release` would build it, built in memory and
not written. `required` lines must pass before the Sign button enables; the rest inform.

reports/tests.json (`ledger test` writes it, testreport.py): {"ok", "count", "failures", "skipped", "golden", "at", "git", "dirty"}.
Absent means "not run": grey, does not block. Failing: red. Passing on another commit or a dirty tree: stale, informs
(tests_line)."""
import csv
import io
import json
import re
import shutil
import threading
from datetime import datetime, timezone

from ..web import api
from . import limitations, taxonomy
from ..checks import proof
from ..review import resolutions
from ..core import store
from ..extract.agent import model
from ..core.config import SCOPE
from ..checks.evidence import load_all
from ..extract.extract import prompt_version
from ..ingest.tables import PARSER_VERSION
from .release import GATES, RELEASES, build, content_hash, failing, gates, limitations_md, readme, rows_diff, rows_diff_md, version_key
from ..review.review import apply, decisions, open_items
from ..checks.rules import load as load_rules

VERSION = re.compile(r"^v\d+\.\d+\.\d+$")
GOLDEN = store.ROOT / "reports" / "golden.json"
TESTS = store.ROOT / "reports" / "tests.json"
GATE_FIX = {"G1": "proof", "G4": "reconcile", "G5": "proof", "G6": "reconcile?cause=asset_types"}  # the page that fixes each gate's items
GATE_SHORT = {"G1": "All filings read", "G4": "Every block has a decision", "G5": "Values confirmed on filing", "G6": "No proposal left to confirm"}


def _rows(con, sql, p):
    cur = con.execute(sql, p)
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _releases() -> list:
    """Every release folder under RELEASES (this module's, so tests point it elsewhere) whose name is a version, oldest
    first; a `v1.8.0-old` or a stray file is not a release and never blocks the next version."""
    return sorted((p for p in RELEASES.glob("v*") if p.is_dir() and VERSION.match(p.name)), key=lambda p: version_key(p.name))


def _manifest(d) -> dict | None:
    """A folder's manifest.json as a dict with a str hash, or None when it is missing, unreadable or not that shape."""
    try:
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, AttributeError):  # ValueError covers JSONDecodeError
        return None
    return m if isinstance(m, dict) and isinstance(m.get("hash"), str) else None


def _readable(d) -> bool:
    """A folder the checklist can diff against: a manifest of the right shape and a values.csv."""
    return _manifest(d) is not None and (d / "values.csv").is_file()


def next_version() -> str:
    """The version to sign next: the lowest unsigned release folder newer than the last signed one (a packet `ledger
    release` built and nobody signed is signed, not skipped; an unsigned folder older than a signed release was
    superseded and stays as it is), else the minor bump of the last folder (v1.7.0 → v1.8.0); v0.1.0 when there is none."""
    rel = _releases()
    signed = [p for p in rel if (p / "SIGNOFF.json").exists()]
    last_signed = version_key(signed[-1].name) if signed else [-1]
    unsigned = [p for p in rel if not (p / "SIGNOFF.json").exists() and version_key(p.name) > last_signed]
    if unsigned:
        return unsigned[0].name
    if not rel:
        return "v0.1.0"
    major, minor, _ = version_key(rel[-1].name)
    return f"v{major}.{minor + 1}.0"


def folder_state(version: str, h: str) -> tuple[str, str]:
    """What releases/<version>/ holds against the packet's hash: (state, note). state: none | same | different | signed |
    broken (no manifest.json: half a write, or a hand-made folder)."""
    d = RELEASES / version
    if not d.exists():
        return "none", ""
    if (d / "SIGNOFF.json").exists():
        return "signed", f"{version} is already signed; a shipped release is never edited. Use a new version."
    if not (d / "manifest.json").exists():
        return "broken", f"releases/{version}/ has no manifest.json: unsigned, broken; delete and rebuild"
    m = _manifest(d)
    if m is None:
        return "broken", f"releases/{version}/manifest.json cannot be read as a manifest: unsigned, broken; delete and rebuild"
    if m["hash"] != h:
        return "different", f"releases/{version}/ is unsigned, built before this release's checks; delete and rebuild"
    return "same", f"releases/{version}/ exists unchanged, unsigned"


def previous_of(version: str):
    """The last readable release folder before `version` by number (a manifest of the right shape and a values.csv,
    signed or not), or None. A broken folder is skipped here and named by `broken_before` as a red line."""
    before = [p for p in _releases() if version_key(p.name) < version_key(version) and _readable(p)]
    return before[-1] if before else None


def broken_before(version: str) -> list[str]:
    """The release folders before `version` the checklist cannot read: delete and rebuild each, or the diff lies."""
    return [p.name for p in _releases() if version_key(p.name) < version_key(version) and not _readable(p)]


def packet(con, version: str, stage: int = 3) -> dict:
    """The release as `ledger release` builds it, in memory: {version, files, hash, manifest, gates, previous}. The
    scope is config.SCOPE and nothing else (T2); DIFF.md carries the values diff, the files diff and the rows diff (T8)."""
    tickers = [list(SCOPE)]
    values = _rows(con, 'select * from "values" where ticker in (select unnest(?))', tickers)
    excs = _rows(con, "select * from exceptions where ticker in (select unnest(?))", tickers)
    exts = _rows(con, "select * from extractions where ticker in (select unnest(?))", tickers)
    ds = decisions()
    hc_path = store.ROOT / "golden" / f"stage{stage}-handcheck.json"
    cells = {e["extraction_id"]: e["cell_text"] for e in exts}
    confirmed = {i for i, r in load_all().items() if r["match"] and cells.get(i) == r["cell"]}
    hc = json.loads(hc_path.read_text()) if hc_path.exists() else None
    g = gates(values, open_items(excs, ds), hc, confirmed, resolutions.unconfirmed(), mappings=taxonomy.to_confirm(con, list(SCOPE)))
    prev_dir = previous_of(version)
    previous = list(csv.DictReader((prev_dir / "values.csv").open())) if prev_dir else None
    ai = _rows(con, "select * from ai_spend where ticker in (select unnest(?))", tickers)
    facts = _rows(con, "select * from facts where ticker in (select unnest(?))", tickers)
    applied = apply(values, excs, ds)
    files = build(version, applied, exts, excs, previous, confirmed, ai, facts, hc, str(hc_path.relative_to(store.ROOT)) if hc else None)
    want = set(tickers[0])
    for name in api.RELEASE_LISTS:  # one shape (C7): the release holds every list the API serves, as the API serves it
        rows = [r for r in api.fetch(con, name) if r.get("ticker", "") in want]
        files[f"{name}.csv"] = api.to_csv(rows)
    files["LIMITATIONS.md"] = limitations_md(version, files)  # T68: counts over the lists as they ship
    files["README.md"] = readme(version, applied, ai, files)  # T64: the column tables come from the headers that ship, so after every CSV is in
    diff = {}
    if prev_dir:  # the shape of the packet is part of the diff
        prev_m = _manifest(prev_dir)
        before = set(prev_m.get("files") or []) - {"manifest.json", "SIGNOFF.json"}
        gone, new = sorted(before - set(files)), sorted(set(files) - before)
        if gone or new:
            files["DIFF.md"] += "\n".join(["", "## Files"] + [f"- added `{f}`" for f in new] + [f"- removed `{f}`" for f in gone] + [""])
        if "provenance" not in prev_m:  # T66: the previous manifest named the build-time versions, not what produced its rows
            files["DIFF.md"] += provenance_note(prev_dir.name, version)
        diff = rows_diff(files, {f.name: f.open(newline="").read() for f in prev_dir.glob("*.csv")})
        files["DIFF.md"] += rows_diff_md(diff)
    h = content_hash(files)
    # The manifest is not among the hashed files: git head/dirty and the input hashes never move the packet's hash (G7), so
    # the Release page's hash is the CLI's within one checkout.
    manifest = {"version": version, "stage": stage, "scope": list(SCOPE), "hash": h, "files": sorted(files), "prompt": prompt_version(), "parser": PARSER_VERSION,
                "model": model(), "rules": {r["id"]: r["file_sha256"][:12] for r in load_rules()}, "decisions": len(ds),
                "provenance": provenance([v for v in values if v.get("value") is not None], exts, facts, **_provenance_rows(con, tickers))}  # values.csv is api.fetch's set: value not null (C7)
    return {"version": version, "files": files, "hash": h, "manifest": manifest, "gates": g, "previous": prev_dir.name if prev_dir else None, "rows_diff": diff,
            "hand_check": hc_path.exists(), "values": len(values)}


# ── T66: what produced the shipped rows. The top-level prompt / parser / model name the versions in use at build time and
# stay for compatibility; `provenance` is the record. ─────────────────────────────────────────────────────────────────
READERS = {"reader": "extract", "notes_reader": "notes", "ai_reader": "aispend", "projects_reader": "projects"}  # agents.json id → runs.step
INPUT_FILES = ("definitions/companies.yaml", "decisions/resolutions.jsonl")  # plus every taxonomy/*.yaml


def provenance_note(previous: str, version: str) -> str:
    """The DIFF.md paragraph when the previous release's manifest has no `provenance`."""
    return f"\nProvenance: {previous}'s manifest named the versions in use at build time; from {version} the manifest names the versions that produced the rows (`manifest.json` `provenance`).\n"


def _provenance_rows(con, tickers: list) -> dict:
    """The rows behind the packet's other lists, the same scope filter the packet applies: note_extractions (behind facts.csv),
    ai_statements (statements.csv), projects (projects.csv), the documents of the companies in scope, and the runs' versions."""
    return {"note_exts": _rows(con, "select extraction_id, accession, prompt_version, run_id from note_extractions where ticker in (select unnest(?))", tickers),
            "statements": _rows(con, "select text_id, prompt_version, run_id from ai_statements where ticker in (select unnest(?))", tickers),
            "projects": _rows(con, "select text_id, prompt_version, run_id from projects where ticker in (select unnest(?))", tickers),
            "documents": _rows(con, "select accession, parser_version from documents where ticker in (select unnest(?))", tickers),
            "runs": _rows(con, "select run_id, step, subject, versions from runs where step in ('extract', 'notes', 'aispend', 'projects')", [])}


def _cited(rows: list[dict], by_id: dict) -> list[dict]:
    """The distinct extraction rows a shipped list cites (values → extractions, facts → note_extractions)."""
    from .release import split_ids
    out = {}
    for r in rows:
        for i in split_ids(r.get("extraction_ids") or ""):
            if i in by_id:
                out[i] = by_id[i]
    return list(out.values())


def provenance(values, exts, facts, note_exts=(), statements=(), projects=(), documents=(), runs=(), git=None, inputs=None) -> dict:
    """{prompts: {reader: [prompt_version...]}, models: [...], parser_versions: [...], unrecorded: {reader: n}, git: {head, dirty},
    inputs: {path: sha256}} over the rows the packet writes: values' cited statement cells, facts' cited note cells, every
    ai_statement and project in scope, the documents of the companies in scope. A row's model is the `versions.model` of the
    run that wrote it (runs by run_id, step, subject). A row with no prompt_version or no model on record counts once under
    `unrecorded` for its reader and is never guessed. `git` and `inputs` are read from the checkout unless passed."""
    versions = {}
    for r in runs:
        try:
            versions[(r["run_id"], r["step"], r["subject"])] = json.loads(r["versions"] or "{}")
        except (ValueError, TypeError):
            versions[(r["run_id"], r["step"], r["subject"])] = {}
    sets = {"reader": (_cited(values, {e["extraction_id"]: e for e in exts}), "accession"),
            "notes_reader": (_cited(facts, {e["extraction_id"]: e for e in note_exts}), "accession"),
            "ai_reader": (list(statements), "text_id"), "projects_reader": (list(projects), "text_id")}
    prompts, models, unrecorded = {}, set(), {}
    for reader, (rows, subject) in sets.items():
        step, seen, n = READERS[reader], set(), 0
        for r in rows:
            m = (versions.get((r.get("run_id"), step, r.get(subject))) or {}).get("model")
            if r.get("prompt_version"):
                seen.add(r["prompt_version"])
            if m:
                models.add(m)
            if not r.get("prompt_version") or not m:
                n += 1
        prompts[reader], unrecorded[reader] = sorted(seen), n
    head, dirty = git_state() if git is None else git
    return {"prompts": prompts, "models": sorted(models), "parser_versions": sorted({d["parser_version"] for d in documents if d.get("parser_version")}),
            "unrecorded": unrecorded, "git": {"head": head, "dirty": dirty}, "inputs": input_hashes() if inputs is None else inputs}


def git_state() -> tuple:
    """(short sha of HEAD, dirty) of this checkout; (None, None) without git (the hosted copy ships no .git)."""
    from .testreport import git_state as _gs
    return _gs()


def input_hashes(root=None) -> dict:
    """sha256 of the inputs a person edits between runs: definitions/companies.yaml, every taxonomy/*.yaml,
    decisions/resolutions.jsonl; null for a file that does not exist (resolutions.jsonl is rebuilt, not tracked)."""
    import hashlib
    root = root or store.ROOT
    paths = [INPUT_FILES[0]] + sorted(p.relative_to(root).as_posix() for p in (root / "taxonomy").glob("*.yaml")) + [INPUT_FILES[1]]
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() if (root / p).is_file() else None for p in paths}


def write(p: dict) -> dict:
    """releases/<version>/ from a packet, written whole: into a temporary folder beside it, then renamed into place, so
    a folder that exists always has every file or none. One that exists with the same hash is left alone; a signed one,
    a broken one or one with different content is refused with the reason `folder_state` gives."""
    state, note = folder_state(p["version"], p["hash"])
    if state == "same":
        return {"written": False, "hash": p["hash"]}
    if state != "none":
        raise ValueError(note)
    out = RELEASES / p["version"]
    tmp = RELEASES / f".{p['version']}.writing"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        for name, text in p["files"].items():
            (tmp / name).write_text(text)
        (tmp / "manifest.json").write_text(json.dumps(p["manifest"], indent=1))
        tmp.rename(out)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return {"written": True, "hash": p["hash"]}


def _report(path) -> dict | None:
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except (json.JSONDecodeError, OSError):
        return None


def _line(id_, label, required, count, state, link, note="", detail=None) -> dict:
    """state: one of states.LINE (pass | fail | info | not_run | stale). A required line passes only on `pass`."""
    from ..core.states import LINE
    if state not in LINE.names():
        raise ValueError(f"checklist line {id_}: state {state!r} is not declared in states.LINE")
    return {"id": id_, "label": label, "required": required, "count": count, "state": state, "ok": state == "pass", "link": link, "note": note, "detail": detail or []}


_LOOKUP = object()  # tests_line's default: read HEAD from this checkout; tests pass a sha or None instead


def tests_line(t: dict | None, head=_LOOKUP, changed=_LOOKUP) -> dict:
    """The "Test run" line (T30) from reports/tests.json as `ledger test` writes it (testreport.py). Three cases:
    The line is required in every case: only a passing run on the code being signed lets a release sign.
    absent or unreadable: "not run", blocks.
    Ran and failed: red, whatever commit it ran on: a known failure never signs.
    Ran and passed on this HEAD with a clean tree: green. Passed on another commit, or on a dirty tree: "stale", blocks
    with the note "run `ledger test`", since the code it tested is not the code being signed. One forgiveness: when every commit since the run changed only reports/tests.json (the commit
    that records the run), the code is the same and the line is green. Without git on either side (the hosted copy has
    no .git) the commit cannot be compared: informs, "commit not compared: no git", never a verified pass.
    `head` and `changed` are read from the checkout unless a test passes them."""
    if t is None:
        return _line("tests", "Test run", True, 0, "not_run", "proof", "not run (reports/tests.json; `ledger test` writes it)")
    fails = t.get("failures") or []
    golden = t.get("golden")
    g_note = {True: "golden ok", False: "golden FAILED"}.get(golden, "golden skipped, see the Golden line")
    sha = t.get("git")
    head = _head() if head is _LOOKUP else head
    base = f"{t.get('count')} tests, {len(fails)} failing, {g_note}, {t.get('at')}" + (f", on {sha}" if sha else "")
    detail = [{"test": f} for f in fails]
    if not t.get("ok"):
        return _line("tests", "Test run", True, len(fails), "fail", "proof", base, detail)
    if not sha or not head:  # no git on one side (the hosted copy ships no .git): the commit cannot be compared, so this is never a verified pass
        return _line("tests", "Test run", True, 0, "info", "proof", f"commit not compared: no git; {base}", detail)
    moved = sha != head
    if moved:
        ch = _changed_since(sha) if changed is _LOOKUP else changed
        moved = ch is None or any(p != "reports/tests.json" for p in ch)
    stale = moved or bool(t.get("dirty"))
    if stale:
        why = "dirty tree" if t.get("dirty") else f"HEAD is {head}"
        return _line("tests", "Test run", True, 0, "stale", "proof", f"stale ({why}): run `ledger test`; {base}", detail)
    return _line("tests", "Test run", True, 0, "pass", "proof", base, detail)


def golden_line(g: dict | None) -> dict:
    """"Golden test": required, green only when the tables are equal AND gold passes (every item has a verdict and every
    verdict holds). Gold unverified (0 of N verdicts, or some missing) is red: "Not a pass" means not a pass, so Sign
    stays disabled until a person gives the verdicts. A report from before T82's split (no tables_ok) is read strictly."""
    if g is None:
        return _line("golden", "Golden test", True, 1, "fail", "proof", "not run")
    tables = bool(g.get("tables_ok") if "tables_ok" in g else g.get("ok")) and not g.get("failed_step")
    gd = g.get("gold") or {}
    state = gd.get("state") or "not run"
    gold_word = {"pass": f"gold pass, {gd.get('checked')} verdicts hold", "fail": f"gold FAILS, {len(gd.get('failures') or [])} verdicts",
                 "unverified": f"gold unverified {gd.get('unverified')} of {gd.get('items')}: give the verdicts on Proof"}.get(state, "gold not run")
    ok = tables and state == "pass"
    note = f"tables {'equal' if tables else 'differ'}" + (f", failed at {g['failed_step']}" if g.get("failed_step") else "") + f"; {gold_word}; {g.get('at')}"
    detail = [{"table": k, "only_in_run": v.get("n_only_in_run"), "only_in_expected": v.get("n_only_in_expected")} for k, v in (g.get("diffs") or {}).items()] \
        + [{"gold": f} for f in gd.get("failures") or []]
    count = 0 if ok else (len(g.get("diffs") or {}) + len(gd.get("failures") or []) + (gd.get("unverified") or 0)) or 1
    return _line("golden", "Golden test", True, count, "pass" if ok else "fail", "proof", note, detail)


def claims_lines() -> list[dict]:
    """"Claims register: every shown claim has a row" (required: red on any scanned string with no row, a row whose words
    are not where it says, a built row with nothing to look for, a scan that read nothing, a findings log edited in an
    earlier commit, or a register that does not load) and "Known gaps" (informs: stub, stale and open findings, now).
    Anything the register raises reads red, never a crash."""
    from . import claims
    label = "Claims register: every shown claim has a row"
    try:
        es = claims.load()
        fs = claims.findings(ids={e["id"] for e in es})
        probs = claims.unregistered(es)
        sc = claims.scan()
        ao = claims.append_only()
        rows = claims.computed(True, entries=es, fs=fs)
    except Exception as e:
        return [_line("claims", label, True, 1, "fail", "gaps", f"the register could not be read: {e.__class__.__name__}: {str(e)[:160]}", [{"problem": str(e)[:300]}])]
    probs = probs + [{"kind": "append_only", "what": p, "where": "claims/findings.jsonl"} for p in ao["problems"]]
    c = claims.counts(rows, fs)
    scanned = f"scanned {sc['pages']} pages and {sc['files'] - sc['pages']} other files, {len(sc['strings'])} strings; {len(rows)} claims; {ao['note']}"
    reg = _line("claims", label, True, len(probs), "pass" if not probs else "fail", "gaps",
                scanned if not probs else f"{len(probs)} problems: a claim with no row, a row whose words moved, or an edited finding; {scanned}",
                [{"kind": p["kind"], "what": p["what"], "where": p["where"]} for p in probs])
    gaps = _line("known_gaps", f"Known gaps: {c['stub']} stub · {c['stale']} stale · {c['open_findings']} open findings", False,
                 c["stub"] + c["stale"] + c["open_findings"], "info", "gaps", claims.counts_line(c) + "; LIMITATIONS.md lists the stub, stale and planned claims",
                 [{"claim": r["claim"], "status": r["status"], "ticket": r["ticket"]} for r in rows if r["status"] in ("stub", "stale")])
    return [reg, doc_line(), gaps]


def doc_line(doc=None, text=None) -> dict:
    """"Claims doc current" (required): docs/CLAIMS.md equals claims.markdown() now. The file merges by union
    (.gitattributes), so a merge can leave duplicate or stale rows; this line blocks signing until `ledger claims` runs."""
    from . import claims
    label = "Claims doc current"
    try:
        want = claims.markdown() if text is None else text
        doc = claims.DOC if doc is None else doc
        have = doc.read_text() if doc.exists() else None
    except Exception as e:
        return _line("claims_doc", label, True, 1, "fail", "gaps", f"could not compare: {e.__class__.__name__}: {str(e)[:160]}")
    if have == want:
        return _line("claims_doc", label, True, 0, "pass", "gaps", "docs/CLAIMS.md equals the register as it is now")
    return _line("claims_doc", label, True, 1, "fail", "gaps", "docs/CLAIMS.md is missing" if have is None else "docs/CLAIMS.md differs from the register: run `ledger claims` and commit")


def _head() -> str | None:
    """Short sha of this checkout's HEAD, or None without git (the hosted copy ships no .git)."""
    from .testreport import git_state
    return git_state()[0]


def _changed_since(sha: str) -> list | None:
    from .testreport import changed_since
    return changed_since(sha)


def review_counts(board: dict, unconfirmed: list, unmapped: list = ()) -> dict:
    """{bad, wait, blocked, per_company, off_board}: the Proof board's items by the row word every page shows
    (states.row), counted with states.tally (Reconcile's header counts its rows the same way), plus a run's decisions to
    confirm under wait (Reconcile's "To confirm" rows, Proposed there; no Proof item carries them, so nothing is counted
    twice), plus under bad every unmapped asset type (taxonomy.unmapped) the board has no mapping row for (`off_board`):
    a name with no entry blocks whether or not a page lists it."""
    from ..core.states import row as row_word, tally
    words = {c["ticker"]: [row_word(i["state"], i.get("by")) for s in c["stages"].values() for i in s["all"]] for c in board["proven"]}
    on_board = {(c["ticker"], i.get("name")) for c in board["proven"] for i in (c["stages"].get("mapping") or {}).get("all", [])}
    off = [m for m in unmapped if (m["ticker"], m["reported_name"]) not in on_board]
    n = tally(w for ws in words.values() for w in ws)
    return {"bad": n.get("bad", 0) + len(off), "wait": n.get("wait", 0) + len(unconfirmed), "blocked": n.get("blocked", 0), "off_board": off,
            "per_company": [{"ticker": t, "open": ws.count("bad") + sum(m["ticker"] == t for m in off), "proposed": ws.count("wait"), "blocked": ws.count("blocked")} for t, ws in words.items()]}


def g6_link(unconfirmed: list, mappings: list) -> str:
    """The page that fixes G6's items: Reconcile with every cause when it holds both a run's decisions and asset types,
    else the one group that holds them."""
    return "reconcile" if unconfirmed and mappings else "reconcile?cause=to_confirm" if unconfirmed else "reconcile?cause=asset_types"


def g6_detail(unconfirmed: list, mappings: list) -> list[dict]:
    """G6's items one per key: the key, its state, the reason and the page that fixes it."""
    return ([{"key": r["key"], "state": r["state"], "reason": (r.get("reason") or "")[:160], "link": "reconcile?cause=to_confirm"} for r in unconfirmed]
            + [{"key": f"asset_types|{m['ticker']}|{m['reported_name']}", "state": "to confirm", "reason": f"{m.get('standard_type')} proposed by {m.get('by')}",
                "link": f"reconcile?scope={m['ticker']}&cause=asset_types"} for m in mappings])


def checklist(con, version: str | None = None, stage: int = 3) -> dict:
    """The checklist for `version` (default: the next version). JSON the page renders as it is."""
    version = version or next_version()
    if not isinstance(version, str) or not VERSION.match(version):
        raise ValueError(f"not a version: {version!r} (vMAJOR.MINOR.PATCH)")
    p = packet(con, version, stage)
    board = proof.board(con)
    lines = []
    from ..core.states import word
    # gates per company (T4): one line per gate, the failing companies named. G6 is the Proposed bucket (a run's decisions
    # and asset-type mappings no person confirmed): its line carries Reconcile's word for it, and no other line counts it
    bad = failing(p["gates"])
    unc = resolutions.unconfirmed()  # a run's decisions to confirm (T3): Reconcile's "To confirm" rows, Proposed there too
    utc = taxonomy.to_confirm(con, list(SCOPE))  # T63: the asset-type mappings no person confirmed, the rest of G6
    for gid in GATES:
        by_t = p["gates"][gid]
        n = sum(len(v) for v in by_t.values())
        detail = [{"ticker": t, "items": len(items), "example": items[0] if items else ""} for t, items in by_t.items()]
        if gid == "G6":  # the Proposed bucket: one row per key, as the line had before T-RS, each with its page
            detail = g6_detail(unc, utc)
        lines.append(_line(f"gate_{gid}", word("row", "wait") if gid == "G6" else GATE_SHORT[gid], True, n, "pass" if n == 0 else "fail", g6_link(unc, utc) if gid == "G6" else GATE_FIX[gid],
                           GATES[gid] + (f"; export the hand-check from reports/stage{stage}-validation.html to golden/stage{stage}-handcheck.json" if gid == "G5" and any(v == ["no hand-check file"] for v in by_t.values()) else ""), detail))
    # open, proposed and blocked in scope (T1): the one definition of open, from the Proof board, split by the row word every
    # page shows (states.row) and counted with states.tally, the function Reconcile's header counts with. Each line is a
    # distinct set, named as Reconcile names its bucket: Needs review (open, nothing proposed; an unmapped asset type is one),
    # Proposed (the G6 line above: an asset-type mapping or a run's decision no person confirmed), Blocks release. Before,
    # "Items to review" counted Needs review and Proposed together, and "Decisions left to confirm" and G6 counted Proposed
    # twice more.
    um = taxonomy.unmapped(con, list(SCOPE))     # T14: the unmapped asset types, counted under Needs review whether or not the board lists them
    rc = review_counts(board, unc, um)
    open_, blocked, per_co = rc["bad"], rc["blocked"], rc["per_company"]  # rc["wait"] is the G6 line's count (tests.test_checklist.Parity)
    lines.append(_line("open", word("row", "bad"), True, open_, "pass" if open_ == 0 else "fail", "reconcile",
                       "Neither verified nor explained, nothing proposed" + (f"; {len(um)} of them asset types with no entry (Reconcile, asset types)" if um else ""),
                       [{"ticker": x["ticker"], "open": x["open"]} for x in per_co if x["open"]] + [{"unmapped": m} for m in um]))
    lines.append(_line("blocked", word("row", "blocked"), True, blocked, "pass" if blocked == 0 else "fail", "reconcile", "A block rule or a decision refuses the release", [{"ticker": x["ticker"], "blocked": x["blocked"]} for x in per_co if x["blocked"]]))
    # completeness against the answer key (T81): an XBRL value with no released value and nothing open is a silent blank
    miss = proof.missing_from_dataset(con, SCOPE, decisions())
    lines.append(_line("complete", "Answer-key values missing from the dataset", True, len(miss), "pass" if not miss else "fail", "reconcile",
                       "company, field and year (from its first 10-K) where XBRL holds a value and the release ships none, with no open item, "
                       "no person's resolution and no person's review decision on it; a company with no XBRL answer loaded counts once",
                       [{"ticker": m["ticker"], "field": m["field"], "period": m["period"], "reference": m["reference"], "why": m["why"]} for m in miss]))
    # rows with no value, by measure (T15: informational)
    tax = list(csv.DictReader(io.StringIO(p["files"]["taxonomy.csv"])))
    nv = {}
    for r in tax:
        if r.get("has_value") == "False":
            nv[r["measure"]] = nv.get(r["measure"], 0) + 1
    lines.append(_line("no_value", "Rows with no value", False, sum(nv.values()), "info", "data?list=taxonomy&has_value=false", "kept with value empty and has_value false; a project without an amount, a statement in words",
                       [{"measure": k, "rows": v} for k, v in sorted(nv.items())]))
    # diff from the previous release in rows (T8)
    d = p["rows_diff"]
    n_diff = sum(x["added"] + x["removed"] + x["changed"] for x in d.values())
    lines.append(_line("diff", f"Rows changed since {p['previous']}" if p["previous"] else "First release", False, n_diff, "info", "data",
                       "added + removed + changed across the lists; DIFF.md carries the same table and examples",
                       [{"list": k, "rows": x["rows"], "added": x["added"], "removed": x["removed"], "changed": x["changed"], "columns_added": x["columns_added"], "columns_removed": x["columns_removed"]} for k, x in d.items()]))
    # known weaknesses with no mitigation (T68: informational, never red)
    lim = limitations.unmitigated(limitations.resolved(p["files"]))
    lines.append(_line("limitations", "Limitations with no mitigation", False, len(lim), "info", "release",
                       "entries of taxonomy/limitations.yaml whose mitigation is none; LIMITATIONS.md in the packet lists every entry",
                       [{"id": e["id"], "closes": e["closes"]} for e in lim]))
    # the claims register (docs/BUILD.md): every claim a page shows has a row (required); what is not yet true (informs)
    lines.extend(claims_lines())
    # golden and the last test run (T30)
    g = _report(GOLDEN)
    lines.append(golden_line(g))
    t = _report(TESTS)
    lines.append(tests_line(t))
    # a release folder before this one the checklist cannot read: the diff would lie, so it is a red line, not a 500
    broken = broken_before(version)
    lines.append(_line("previous", "Previous releases readable", True, len(broken), "fail" if broken else "pass", "release",
                       "; ".join(f"previous release {v} is broken: delete and rebuild" for v in broken) if broken else f"diffed against {p['previous']}" if p["previous"] else "no previous release",
                       [{"folder": v} for v in broken]))
    # the packet as it would be written
    fstate, fnote = folder_state(version, p["hash"])
    exists, signed = fstate != "none", fstate == "signed"
    pk_state = "pass" if fstate in ("none", "same") else "fail"
    pk_note = fnote or f"built in memory, not written; {p['values']} values, {len(tax)} taxonomy rows"
    lines.append(_line("packet", f"Packet {version}", True, len(p["files"]), pk_state, "data", pk_note,
                       [{"file": n, "bytes": len(text.encode()), "rows": max(0, text.count("\n") - 1) if n.endswith(".csv") else None} for n, text in sorted(p["files"].items())]))
    required = [l for l in lines if l["required"]]
    return {"version": version, "previous": p["previous"], "scope": list(SCOPE), "stage": stage, "hash": p["hash"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ok": all(l["ok"] for l in required), "red": [l["id"] for l in required if not l["ok"]], "lines": lines,
            "gates": {"table": p["gates"], "failing": bad}, "open": open_, "blocked": blocked, "unconfirmed": sum(len(v) for v in p["gates"]["G6"].values()), "unmapped": len(um),
            "diff": d, "golden": g, "tests": t, "exists": exists, "signed": signed, "folder": fstate}


def checklist_table(cl: dict) -> str:
    """The checklist as text, for `ledger release`: one line per check, state, count, label, note."""
    w = max(len(l["label"]) for l in cl["lines"])
    return "\n".join([f"{cl['version']} checklist: " + ("every required line green" if cl["ok"] else f"red on {', '.join(cl['red'])}")]
                     + [f"  {l['state']:7} {l['count']:>6}  {l['label'].ljust(w)}  {l['note'][:70]}" for l in cl["lines"]])


def summary(cl: dict) -> dict:
    """What a signature meant (T7): the counts Proof's releases table shows, from the checklist as it was at signing."""
    return {"open": cl.get("open", 0) + cl.get("blocked", 0), "unmapped": cl.get("unmapped"), "scope": cl.get("scope") or [], "unconfirmed": cl.get("unconfirmed"), "at": cl.get("at")}


_LOCK = threading.Lock()  # one signature at a time: two clicks never race the write, the signoff and the publish


def _red(cl: dict) -> str:
    return f"{cl['version']} not signed: {', '.join(cl['red'])} " + ("is" if len(cl["red"]) == 1 else "are") + " red on the checklist"


def _compact(cl: dict) -> dict:
    """The checklist as SIGNOFF.json stores it: the diff's counts, not its examples (DIFF.md has those)."""
    return {**cl, "diff": {k: {kk: vv for kk, vv in x.items() if kk != "examples"} for k, x in cl["diff"].items()}}


def sign(con, version: str | None, by: str, stage: int = 3) -> dict:
    """The Sign button (T6): build the checklist; refuse (ValueError → 400) while any required line is red or no name is
    given; else write releases/<version>/, build the checklist again on what is now on disk and refuse if anything went
    red meanwhile (the folder stays, unsigned, the next version to sign), sign it as `by` with that checklist, and publish.
    `by` is the page's signer box today, recorded as given; who may press the button is a later ticket (auth). A publish
    that fails after the signature lands is recorded in SIGNOFF.json (published false, publish_error) and reported, not
    hidden: the release is signed and unpublished until `ledger publish` succeeds. Serialized: one signature at a time."""
    from ..cli.signoff import record, sign as _signoff
    from .publish import NotPublishable, publish
    if not isinstance(by, str) or not by.strip():
        raise ValueError("a signature needs a name")
    with _LOCK:
        cl = checklist(con, version, stage)
        if not cl["ok"]:
            raise ValueError(_red(cl))
        p = packet(con, cl["version"], stage)
        if p["hash"] != cl["hash"]:
            raise ValueError("the data changed while the checklist was built; reload and sign again")
        write(p)
        cl = checklist(con, cl["version"], stage)  # the second pass, on the folder as written
        if not cl["ok"] or cl["hash"] != p["hash"]:
            raise ValueError(_red(cl) if not cl["ok"] else "the data changed while the release was written; reload and sign again")
        s = _signoff(cl["version"], by.strip(), _compact(cl))
        out = {"version": cl["version"], "hash": p["hash"], "signed_by": s["signed_by"], "signed_at": s["signed_at"], "published": False, "rows": None, "publish_error": None}
        try:
            rows = publish(cl["version"])["rows"]
        except (NotPublishable, SystemExit, Exception) as e:  # psycopg errors included: the signature stands, the publish is retried with `ledger publish`
            out["publish_error"] = str(e) or e.__class__.__name__
            fields = {"published": False, "publish_error": out["publish_error"]}
        else:
            out |= {"published": True, "rows": rows, "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            fields = {"published": True, "published_at": out["published_at"], "rows": rows}
        try:  # what happened is in the reply either way; a note that fails to land never undoes a publish that succeeded
            record(cl["version"], **fields)
        except Exception as e:
            out["record_error"] = str(e) or e.__class__.__name__
    return out
