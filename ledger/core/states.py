"""The state machines that reach a page, declared once (docs/STATES.md, M1 to M16).

Each machine names its states, the kind of each (good, neutral, open, bad, or one of the never-good kinds: unknown,
stale, missing), the transitions allowed between them, the one function that computes the state, and the word a page
shows for each state. Pages read the words from here (`/pages/_states.js`, written by `js()` on every request), so a page
cannot keep its own copy; the claims scan reads them from here too (`claims.scan`).

A state may be `alias` of another machine's state: the same thing on a page, so it shares that state's word and tone
(a fact checked by its XBRL tag is the row state `ok`). Every word names exactly one state, or one group whose members
it names (tests.test_states).

The machines:
- row       a dataset row's verification as every page says it (the trail, Reconcile, Proof): `row(state, by)`. Its
            groups are status.STATES (checked, explained, open, blocked), which `status._state` computes (M1).
- ladder    a note figure's rung (M1b): `ladder(st)` on ties.fact_state's state; the taxonomy's check column reads it.
- check     a value's reconcile label against the SEC's XBRL (M1a): reconcile.values_for sets it; `check(label)` reads it.
- mapping   a reported asset type (M5): `mapping(st)` on status.of_mapping's state.
- crop      a cited cell's crop (M14): crops.state.
- gold      a gold item's verdict (M7): `gold(item)`.
- gold_group what independent check a gold item has besides the person (M17): gold.group; the Proof page's group order.
- crosscheck a calculated figure against the filing's own total or SEC XBRL (M18): calc.state.
- line      a Release checklist line (M9): checklist._line refuses an undeclared state.
- edgar     the EDGAR check's freshness (M12): `edgar(checked_at, now)`, read by the trail and the claims register.
- company   whether a ticker has a trail (M19): `company(tracked, documents)`; only a filed company can read Proven.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

GOOD, NEUTRAL, OPEN, BAD = "good", "neutral", "open", "bad"
# V13 (docs/ux-visual/problems.md): red (text-red) is kept for a BAD state, what blocks a release or failed; every open state a
# person must look at reads in one hue, text-review (app.html); a proposal waiting on a person is text-purple
UNKNOWN, STALE, MISSING = "unknown", "stale", "missing"  # never good: not looked up / not run, out of date, gone
KINDS = (GOOD, NEUTRAL, OPEN, BAD, UNKNOWN, STALE, MISSING)
NEVER_GOOD = (UNKNOWN, STALE, MISSING)


@dataclass(frozen=True)
class State:
    name: str
    kind: str
    label: str | None = None  # the page's word; None with `alias`
    tone: str | None = None   # the page's colour class
    alias: str | None = None  # "machine.state": the same thing on a page, its word and tone
    meaning: str = ""


@dataclass(frozen=True)
class Machine:
    id: str
    doc: str                      # the docs/STATES.md section
    compute: str                  # the one function that decides the state, "module.function"
    states: tuple[State, ...]
    transitions: frozenset = frozenset()   # (from, to) pairs a writer may cause; computed machines list their input moves
    groups: dict = field(default_factory=dict)          # group -> (word, (state names))
    absent: str = ""              # the state an absent input gives (never good), or why there is none
    no_unknown_because: str = ""  # a machine with no unknown, stale or missing state says why every absence lands on an open one

    def names(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.states)

    def get(self, name: str) -> State:
        for s in self.states:
            if s.name == name:
                return s
        raise KeyError(f"{self.id}: no state {name!r}")


class IllegalTransition(ValueError):
    pass


def _s(name, kind, label=None, tone=None, alias=None, meaning=""):
    return State(name, kind, label, tone, alias, meaning)


# ── row: the verification ladder every page says (T92; cards.py, Reconcile, Proof) ─────────────────────────────────
VERIFIED_BY = ("xbrl", "quote")  # the only checks a page may call Verified (tests.test_cards.How.test_only_sec_xbrl_and_quotes_read_verified)
ROW = Machine("row", "M1", "ledger.core.states.row", (
    _s("ok", GOOD, "Verified", "text-green", meaning="checked by an SEC XBRL match or a quote that matches its source"),
    _s("corroborated", GOOD, "Corroborated", "text-teal", meaning="checked by a tie to the filing's tagged total, a second filing, or another answer key"),
    _s("company", GOOD, "Matches company tag", "text-cyan", meaning="a category the company's own XBRL tag matches"),
    _s("done", NEUTRAL, "Done", "text-secondary", meaning="found or confirmed, not checked: statements located, no blocking items, a person's confirmation"),
    _s("info", NEUTRAL, "Unverified", "text-azure", meaning="explained: a citation only, a definition, a decision, an info rule"),
    _s("wait", OPEN, "Proposed", "text-purple", meaning="a proposal no person has confirmed (a mapping, a run's decision)"),
    _s("bad", OPEN, "Needs review", "text-review", meaning="open: neither checked nor explained"),
    _s("blocked", BAD, "Blocks release", "text-red", meaning="a block rule fired or a person's decision blocks"),
    _s("unknown", UNKNOWN, "Not checked", "text-secondary", meaning="no state was computed for the row"),
), frozenset({("bad", "info"), ("bad", "blocked"), ("info", "bad"), ("info", "blocked"), ("blocked", "info"), ("blocked", "bad"),
              ("wait", "done"), ("wait", "bad"), ("wait", "info"), ("bad", "ok"), ("bad", "corroborated"), ("info", "ok"), ("info", "corroborated"),
              ("ok", "bad"), ("corroborated", "bad"), ("unknown", "bad")}),
    groups={"checked": ("Checked", ("ok", "corroborated", "company")), "done": ("Located/Done", ("done",)), "explained": ("Unverified", ("info",)),
            "open": ("To review", ("wait", "bad")), "blocked": ("Blocks release", ("blocked",))},
    absent="unknown")
# the page groups as status.STATES groups: Located/Done is status "checked" (nothing open) but no independent check, so a
# page never counts it under the word Checked
STATUS_OF_GROUP = {"checked": "checked", "done": "checked", "explained": "explained", "open": "open", "blocked": "blocked"}
# a person's decision moves a row between explained, open and blocked, never to checked: only a check makes it checked
DECISION_MOVES = {"accept": "explained", "explain": "explained", "fix": "open", "blocks": "blocked"}


def row(state: str | None, by: str | None) -> str:
    """The row's word on every page, from its status state (status._state) and what it rests on (`by`)."""
    from .status import answer_key, method_kind
    by = by or ""
    if state == "blocked":
        return "blocked"
    if state in ("open", "to confirm"):
        return "wait" if by == "label:to_confirm" or state == "to confirm" else "bad"
    if state == "explained":
        return "info"
    if state == "checked":
        if by in VERIFIED_BY:
            return "ok"
        if by == "mapping:filer_tag":
            return "company"
        if method_kind(by) in ("located", "gate", "mapping"):
            return "done"
        if answer_key(by) or method_kind(by) == "reading":
            return "corroborated"
        return "done"
    return "unknown"


def tally(words) -> dict:
    """{row word: count} over row words (states.row's result per row): Reconcile's header (workbench.items by_state)
    and the Release checklist's Needs review / Proposed / Blocks release lines both count with this, so a bucket has
    one name and one number on both pages (tests.test_checklist.Parity)."""
    out: dict = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    return out


BUCKETS = ("bad", "wait", "blocked")  # the open buckets, in this order on every page: Needs review, Proposed, Blocks release


def buckets(pairs) -> dict:
    """{ticker: {bad, wait, blocked}} over (ticker, row word) pairs: the one per-company open count. The Proof board, the
    trail header, Reconcile's header and the Release lines' details all count with this and say each bucket by its row
    word, so GOOGL reads Needs review 7 · Proposed 4 on every page, never 11 on one and 7 or 4 on another
    (tests.test_flow.OneNumber). A company whose rows are all settled still gets its zeros."""
    out: dict = {}
    for t, w in pairs:
        if w not in ROW.names():
            raise ValueError(f"{w!r} is not a row word (states.ROW)")
        b = out.setdefault(t, dict.fromkeys(BUCKETS, 0))
        if w in b:
            b[w] += 1
        elif ROW.get(w).kind in NEVER_GOOD:  # a row nothing decided (Not checked) is open work: Needs review, never counted nowhere
            b["bad"] += 1
    return out


def group(state: str) -> str:
    """The status.STATES group of a row state."""
    for g, (_, members) in ROW.groups.items():
        if state in members:
            return g
    return "unknown"


# ── ladder: a note figure's rung (ties.fact_state); the taxonomy rows' check column reads it ───────────────────────
LADDER = Machine("ladder", "M1b", "ledger.core.states.ladder", (
    _s("xbrl", GOOD, alias="row.ok", meaning="the filing's XBRL tags the same value"),
    _s("filer_tag", GOOD, alias="row.company", meaning="the company's own tag on the category"),
    _s("tie", GOOD, alias="row.corroborated", meaning="the parts tie to the total the same filing tags"),
    _s("reading", GOOD, alias="row.corroborated", meaning="a second filing prints the same figure"),
    _s("keyed", GOOD, alias="row.corroborated", meaning="another answer key agreed"),
    _s("citation_only", NEUTRAL, alias="row.info", meaning="untagged, no tie, one reading: the citation is all"),
    _s("explained", NEUTRAL, alias="row.info", meaning="a decision, a definition or a guard explains it"),
    _s("readings_differ", OPEN, alias="row.bad", meaning="two filings print different figures"),
    _s("differs", OPEN, alias="row.bad", meaning="the cell differs from its tag, or nothing explains it"),
    _s("not_looked_up", UNKNOWN, alias="row.unknown", meaning="the instance was never loaded: not produced yet, it reads citation_only (F17)"),
), frozenset({("citation_only", "tie"), ("citation_only", "reading"), ("citation_only", "readings_differ"), ("readings_differ", "explained"),
              ("differs", "explained"), ("explained", "differs"), ("xbrl", "differs"), ("differs", "xbrl"), ("not_looked_up", "citation_only")}),
    absent="not_looked_up is declared but not produced: a fact whose instance was never loaded reads citation_only (F17, open)")
LADDER_CHECK = {"xbrl": "agree", "filer_tag": "agree", "tie": "corroborated", "reading": "corroborated", "keyed": "corroborated",
                "citation_only": "no_reference", "explained": "explained", "readings_differ": "differs", "differs": "differs",
                "not_looked_up": "not_checked"}  # the taxonomy `check` column; not_checked is the word pit.py gives an unchecked vintage, never a pass


def ladder(st: dict) -> str:
    """The rung of a fact's state (ties.fact_state's first element)."""
    by, s = st.get("by") or "", st.get("state")
    if s == "checked":
        if by == "xbrl":
            return "xbrl"
        if by == "mapping:filer_tag":
            return "filer_tag"
        if by.startswith("rule:") and by.endswith("_tie"):
            return "tie"
        if by.startswith("reading:"):
            return "reading"
        return "keyed"
    if s == "explained":
        return "citation_only" if by == "label:no_reference" else "explained"
    if s in ("open", "blocked"):
        return "readings_differ" if by == "rule:fact_readings_differ" else "differs"
    return "not_looked_up"


# ── check: a value's reconcile label against the SEC's XBRL (reconcile.values_for) ────────────────────────────────
CHECK = Machine("check", "M1a", "ledger.checks.reconcile.values_for", (
    _s("agree", GOOD, alias="row.ok", meaning="the cell agrees with the SEC's XBRL value"),
    _s("unresolved", OPEN, "Differs from SEC XBRL", "text-review", meaning="the cell differs from the SEC's XBRL value"),
    _s("definition_gap", NEUTRAL, "Unverified · definition", "text-azure", meaning="differs, and a definition on file says why"),
    _s("no_reference", NEUTRAL, "Unverified · citation only", "text-azure", meaning="no XBRL value to compare"),
    _s("not_reported", NEUTRAL, "Not reported", "text-secondary", meaning="the company reports no such line and XBRL has none"),
    _s("not_extracted", OPEN, "In SEC XBRL, not extracted", "text-review", meaning="XBRL holds a value the reader did not extract (T65)"),
    _s("unknown", UNKNOWN, alias="row.unknown", meaning="no label: the row was not reconciled"),
), frozenset({("unknown", s) for s in ("agree", "unresolved", "definition_gap", "no_reference", "not_reported", "not_extracted")}
             | {("unresolved", "definition_gap"), ("definition_gap", "unresolved"), ("unresolved", "agree"), ("agree", "unresolved"),
                ("not_extracted", "agree"), ("not_extracted", "unresolved")}),
    absent="unknown")


def check(label: str | None) -> str:
    return label if label in CHECK.names() and label != "unknown" else "unknown"


# ── mapping: a reported asset type (status.of_mapping) ──────────────────────────────────────────────────────────────
MAPPING = Machine("mapping", "M5", "ledger.core.status.of_mapping", (
    _s("confirmed", NEUTRAL, alias="row.done", meaning="a person confirmed the member (confirmed_by)"),
    _s("filer_tag", GOOD, alias="row.company", meaning="the company's own XBRL tags the category with the proposed member"),
    _s("to_confirm", OPEN, alias="row.wait", meaning="an entry no person confirmed (T63)"),
    _s("unmapped", OPEN, "Unmapped", "text-review", meaning="no entry in taxonomy/asset_types.yaml (the trail says the row's word, Needs review)"),
), frozenset({("unmapped", "to_confirm"), ("unmapped", "confirmed"), ("to_confirm", "confirmed"), ("to_confirm", "unmapped"),
              ("to_confirm", "filer_tag"), ("filer_tag", "confirmed")}),
    absent="unmapped",
    no_unknown_because="a missing entry is unmapped and a company tag not checked (no instance on disk) leaves the entry to_confirm: both open, neither reads checked")


def mapping(st: dict) -> str:
    by = st.get("by") or ""
    if st.get("state") == "checked":
        return "filer_tag" if by == "mapping:filer_tag" else "confirmed"
    return "to_confirm" if by == "label:to_confirm" else "unmapped"


# ── crop: a cited cell's picture (crops.state) ─────────────────────────────────────────────────────────────────────
CROP = Machine("crop", "M14", "ledger.checks.crops.state", (
    _s("located", GOOD, "Cell located", "text-green", meaning="the locator found the cited text; the picture is the one written"),
    _s("not_located", BAD, "Cell not located", "text-red", meaning="the locator did not find the cited text there"),
    _s("stale", STALE, "Crop out of date", "text-orange", meaning="the filing, its fingerprint, the citation or the crop code changed since"),
    _s("missing", MISSING, "Crop file missing", "text-orange", meaning="the picture is gone or not the one written"),
    _s("none", UNKNOWN, "No crop", "text-secondary", meaning="no crop on record, or no extraction on file"),
), frozenset({("none", "located"), ("none", "not_located"), ("stale", "located"), ("stale", "not_located"), ("located", "stale"),
              ("not_located", "stale"), ("located", "missing"), ("missing", "located"), ("not_located", "located"), ("located", "not_located")}),
    absent="none")

# ── gold: a gold item's verdict (gold/<TICKER>.json) ────────────────────────────────────────────────────────────────
GOLD = Machine("gold", "M7", "ledger.core.states.gold", (
    _s("unchecked", UNKNOWN, "Unchecked", "text-secondary", meaning="no verdict yet: never a pass"),
    _s("right", GOOD, "Right", "text-green", meaning="the filing shows this number at this cell"),
    _s("wrong", BAD, "Wrong", "text-red", meaning="the filing shows something else"),
    _s("cant_say", NEUTRAL, "Can’t say", "text-secondary", meaning="the filing does not settle it"),
), frozenset({("unchecked", v) for v in ("right", "wrong", "cant_say")} | {(a, b) for a in ("right", "wrong", "cant_say") for b in ("right", "wrong", "cant_say") if a != b}),
    absent="unchecked")


def gold(item: dict | None) -> str:
    v = (item or {}).get("verdict")
    return v if v in ("right", "wrong", "cant_say") else "unchecked"


# ── gold_group: what independent check a gold item has besides the person (gold.group); the hard groups come first ───
GOLD_GROUP = Machine("gold_group", "M17", "ledger.review.gold.group", (
    _s("no_counterpart", NEUTRAL, "No SEC counterpart", "text-azure", meaning="no XBRL value to compare (no_reference, not_reported): the person is the only check"),
    _s("definition", NEUTRAL, "Definition differs", "text-azure", meaning="an XBRL value exists and differs (definition_gap, unresolved)"),
    _s("not_extracted", OPEN, "Not extracted", "text-review", meaning="XBRL holds a value the reader did not extract (not_extracted)"),
    _s("not_reconciled", UNKNOWN, "Not reconciled", "text-secondary", meaning="no label, or a label off the list: the row was never compared"),
    _s("calculated", GOOD, "Calculated", "text-teal", meaning="agrees with SEC XBRL, and its calculation from several cells holds (calc.holds)"),
    _s("xbrl", GOOD, "Matches SEC XBRL", "text-green", meaning="agrees with SEC XBRL: already machine-checked"),
), frozenset({(a, b) for a in ("no_counterpart", "definition", "not_extracted", "not_reconciled", "calculated", "xbrl")
              for b in ("no_counterpart", "definition", "not_extracted", "not_reconciled", "calculated", "xbrl") if a != b}),
    absent="not_reconciled")
GOLD_GROUP_ORDER = ("no_counterpart", "definition", "not_extracted", "not_reconciled", "calculated", "xbrl")
# a gold item's live group may differ from the group of its claim at the draw (gold.groups): the page says so
GROUP_CHANGED = "Group changed since draw"
# ── display words: what a page says about a row that is not a state of it (docs/STATES.md, "Display words") ──────────
# A fact whose readings disagree across filings (ties.restatement) and a segment series across a re-segmentation
# (rules/segment_basis_mixed.yaml) are facts about the row, never its state: the row keeps the state its machine gives
# it. Declared here so `words()` lists them with the state words: the claims scan reads them from this file, and
# tests.test_states.Words holds them to one owner each, like a state word.
DISPLAY = {
    "restated": ("Restated", "the line on a fact whose readings disagree across filings: every figure as filed, oldest first, and the one the dataset uses"),
    "superseded": ("Superseded", "under a reading's crop: a figure the dataset does not use"),
    "source_not_found": ("Source reading not found", "never good: no reading from the fact's own filing carries the dataset's figure, so no reading is called the one used"),
    "segment_basis_mixed": ("Segment basis mixed", "a segment series whose release years come from both sides of a re-segmentation (the rule's finding, open until a person decides)"),
}
RESTATED, SUPERSEDED, SOURCE_NOT_FOUND, SEGMENT_BASIS_MIXED = (DISPLAY[k][0] for k in ("restated", "superseded", "source_not_found", "segment_basis_mixed"))

# ── crosscheck: a calculated figure against a total someone else printed or tagged (calc.state) ──────────────────────
CROSSCHECK = Machine("crosscheck", "M18", "ledger.checks.calc.state", (
    _s("matches", GOOD, "matches", "text-green", meaning="the filing's own total, or SEC XBRL, equals the calculation within rounding"),
    _s("explained", NEUTRAL, "includes", "text-secondary", meaning="the filing's own total differs by exactly one formula input, sign-aware, and by no other line (a wider measure: Amazon's total includes cost of sales)"),
    _s("differs", OPEN, "differs by", "text-review", meaning="the other total differs; the page names the line of that amount only when exactly one line is"),
    _s("none", UNKNOWN, "No total to compare", "text-secondary", meaning="the filing prints no such total in that column, or XBRL has no value"),
), frozenset({(a, b) for a in ("none", "matches", "explained", "differs") for b in ("none", "matches", "explained", "differs") if a != b and b != "none"}),
    absent="none")

# ── line: a Release checklist line (checklist._line) ────────────────────────────────────────────────────────────────
LINE = Machine("line", "M9", "ledger.release.checklist._line", (
    _s("pass", GOOD, "Pass", "text-green"),
    _s("fail", BAD, "Fail", "text-red"),
    _s("info", NEUTRAL, "Info", "text-secondary", meaning="informs, never blocks"),
    _s("not_run", UNKNOWN, "Not run", "text-orange", meaning="the input the line reads does not exist"),
    _s("stale", STALE, "Stale", "text-orange", meaning="the input exists but is from other code (another commit, a dirty tree)"),
), frozenset({(a, b) for a in ("pass", "fail", "info", "not_run", "stale") for b in ("pass", "fail", "info", "not_run", "stale") if a != b and b != "not_run"}),
    absent="not_run")

# ── edgar: how old the EDGAR check is (data/watch.json checked_at; clock.age_hours) ────────────────────────────────
STALE_HOURS = 48
EDGAR = Machine("edgar", "M12", "ledger.core.states.edgar", (
    _s("fresh", GOOD, "SEC checked", "text-secondary", meaning=f"checked within {STALE_HOURS} hours; the page adds the age"),
    _s("stale", STALE, "out of date", "text-orange", meaning=f"older than {STALE_HOURS} hours; the page adds the age"),
    _s("never", UNKNOWN, "SEC never checked", "text-orange", meaning="no check on file"),
    _s("unreadable", MISSING, "SEC check failed", "text-orange", meaning="the time is unreadable, has no zone, or lies in the future"),
), frozenset({("never", "fresh"), ("fresh", "stale"), ("stale", "fresh"), ("unreadable", "fresh"), ("never", "unreadable")}),
    absent="never")


def edgar(checked_at, at=None) -> tuple[str, float | None, str | None]:
    """(state, hours since the check or None, the clock's problem or None) for data/watch.json's `checked_at`."""
    from .clock import age_hours
    hours, problem = age_hours(checked_at, at)
    if problem == "never":
        return "never", None, problem
    if problem:
        return "unreadable", None, problem
    return ("stale" if hours > STALE_HOURS else "fresh"), hours, None


# ── company: whether a ticker can have a trail at all (proof.company, the trail route; F-BF15) ──────────────────────
COMPANY = Machine("company", "M19", "ledger.core.states.company", (
    _s("filed", NEUTRAL, "Filings read", "text-secondary", meaning="a followed company with at least one filing read; its stages decide whether it is proven"),
    _s("unfiled", UNKNOWN, "No filings yet", "text-orange", meaning="a followed company (config.tracked) with no filing read: nothing to prove, never Proven"),
    _s("unknown", UNKNOWN, "Unknown company", "text-review", meaning="a ticker the ledger does not follow and has read no filing for: no trail"),
), frozenset({("unknown", "unfiled"), ("unknown", "filed"), ("unfiled", "filed")}),
    absent="unknown")


def company(tracked: bool, documents: int) -> str:
    """A ticker's company state: filed (at least one filing read, followed or not), unfiled (followed, nothing read yet)
    or unknown (neither). Only a filed company can read Proven."""
    if documents and documents > 0:
        return "filed"
    return "unfiled" if tracked else "unknown"


MACHINES = {m.id: m for m in (ROW, LADDER, CHECK, MAPPING, CROP, GOLD, GOLD_GROUP, CROSSCHECK, LINE, EDGAR, COMPANY)}


def allow(machine: str, frm: str, to: str) -> None:
    """Raise IllegalTransition unless `frm` -> `to` is declared (staying put is always allowed). Declared for every
    machine; enforced at a writer only for gold today (gold.record): the other writers and log replays are still to do."""
    m = MACHINES[machine]
    for s in (frm, to):
        m.get(s)
    if frm != to and (frm, to) not in m.transitions:
        raise IllegalTransition(f"{machine}: {frm} -> {to} is not an allowed transition")


def resolve(machine: str, name: str) -> State:
    """The state that carries the word and tone: the state itself, or the one it is an alias of."""
    s = MACHINES[machine].get(name)
    while s.alias:
        mid, _, sname = s.alias.partition(".")
        s = MACHINES[mid].get(sname)
    return s


def word(machine: str, name: str) -> str:
    return resolve(machine, name).label


def labels() -> dict:
    """{machine: {state: [tone, word]}} plus each machine's groups, for the pages."""
    out = {}
    for mid, m in MACHINES.items():
        out[mid] = {s.name: [resolve(mid, s.name).tone, resolve(mid, s.name).label] for s in m.states}
    return out


def words() -> dict:
    """{word: [(machine, state) that own it]}: aliases resolve to their owner, groups count as their members, and the
    display words (DISPLAY) are owned by ("display", key)."""
    out: dict = {}
    for mid, m in MACHINES.items():
        for s in m.states:
            if s.label:
                out.setdefault(s.label, []).append((mid, s.name))
        for g, (w, members) in m.groups.items():
            out.setdefault(w, []).append((mid, "group:" + g))
    for k, (w, _) in DISPLAY.items():  # display words: not states, owned here all the same
        out.setdefault(w, []).append(("display", k))
    return out


def js() -> str:
    """The page script /pages/_states.js: the words and tones only. The readers (stateWord, stateGroups, stateKnown) live
    in _shared.js and guard with typeof, so a page whose _states.js failed to load still renders, with plain words."""
    groups = {mid: {g: w for g, (w, _) in m.groups.items()} for mid, m in MACHINES.items() if m.groups}
    absent = {mid: m.absent for mid, m in MACHINES.items() if m.absent in m.names()}
    return ("// Written by ledger/core/states.py on every request: the one place a state's word lives. Do not copy these into a page.\n"
            f"const STATES = {json.dumps(labels(), ensure_ascii=False, sort_keys=True)};\n"
            f"const STATE_GROUPS = {json.dumps(groups, ensure_ascii=False, sort_keys=True)};\n"
            f"const STATE_ABSENT = {json.dumps(absent, sort_keys=True)};\n")
