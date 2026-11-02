# How a ticket is built

Every ticket follows this, the builder and the reviewer alike. It exists because the reviews of 2 Nov 2026 found the same
kinds of failure again and again, after the builder had called the work done, and the "fix later" findings lived only in
chat. Two things change that: a pre-mortem before any code, and a claims register that holds what is not yet true.

## 1. Pre-mortem, before code

Before writing anything, write down how the change could lie. Go through the eight patterns below, one by one, and for
each one either say how the change could hit it or say why it cannot. Every way it could hit becomes a test, named in the
ticket's "Done when" before the code exists. "Cannot happen" needs a reason, not a shrug.

| # | Pattern | What it looks like | Real example from this repo |
|---|---|---|---|
| 1 | A label standing in for a check | A status word is set and read as if something was verified | `not_reported` counted as explained while XBRL held the value (Amazon's blank cost of revenue) |
| 2 | A vacuous pass | Nothing to check reads as passed | An empty `gold/` folder, or an empty reference table, made the golden check green |
| 3 | One decision silently closing other items | A key that is too coarse lets one resolution close a sibling | T92: a resolution on one note finding took the slot of every finding on the same field and year |
| 4 | Two consumers disagreeing about one row | Two pages compute the same state their own way | T92: the taxonomy rows and gold said one thing about a fact, Proof another |
| 5 | Degenerate cases | One part, all zeros, a total counted as a part, an empty file | A tie group of one part, or a "Total" line counted as a member, tied to itself |
| 6 | Late or concurrent writes overwriting newer state | An old answer or a parallel writer lands after a newer one | T100: an output for an older task loaded over a newer one; T63: a reject that missed a confirmation written after it looked; T82: a gold draw over a verdict given during it |
| 7 | Wording that claims more than the check proves | The label promises more than the test shows | "The tie verifies each part": a tie bounds the sum, two offsetting misreads still tie |
| 8 | Stale input that looks fresh | An old file or an old server is read as current | The EDGAR check was five days old while the page looked current; a server kept running old code after a merge |

Before the pre-mortem, find the state machines the change touches in `docs/STATES.md` (states, transitions, who may cause each, the UI words each state produces) and name any state or transition the change adds.

## 2. The claims register

`claims/claims.yaml` holds one row per claim the product makes: on a page, in the API, or in a release. Each row has the
claim in the product's own words, where it is shown, the exact strings that show it, what backs it (functions and the
tests that prove it), a declared status, its gaps and the ticket that closes them. `ledger/claims.py` computes the status:

- proven: built, tested, and the evidence walk passes.
- partial: works, with the gaps listed.
- stub: exists, not yet real (for example the gold error rate with 0 of 120 verdicts).
- stale: depends on an input that is out of date (the EDGAR check, the hosted copy).
- planned: not built.

A row with `checks` gets its status from the facts: it starts from proven and each check lowers it (a declared stale is
not a floor; a fresh EDGAR check lifts it). A row without checks starts from its declared status and only gets worse.
Either way a claim is never proven with no test, a test that does not exist, a test that was skipped or failed in the
last `ledger test` run (reports/tests.json records the skipped ids), a function that does not import, a listed gap or an
open finding. The facts the checks read: the gold verdicts, `reports/golden.json` (tables and gold state), the age of
`data/watch.json`, the hosted copy's deploy record (`claims/hosted.json`) and the unconfirmed asset-type mappings. Gaps a
check measures (counts, dates, versions) are written by the check; only what no check measures is typed in `gaps`.

The clock and the commit are live facts. The Gaps page, `/api/v1/claims` and the Release checklist read them; docs/CLAIMS.md
and every packet's LIMITATIONS.md do not (the packet is hashed, so the same data must give the same text at any time on
any commit): there, the EDGAR check and the hosted copy's code read "checked live only".

`claims/findings.jsonl` is the list of open review findings, append-only: one JSON line per finding (id, source, severity,
text in product words, where with the identifiers, claim, ticket, status open / fixed / wontfix, at). To close one,
append a line with the same id that changes only `status` and `at`; the loader refuses a later line that changes anything
else, and every committed version of the file must be a prefix of the working one (checked on the Release checklist;
without git, on the hosted copy, the Gaps page says "not enforced here").

The page scan reads every page's label maps (the trail's tones, Reconcile's states, the Release line states, the XBRL and
check words, the gold verdict words), every element styled as a status (a badge or a tone colour), app.html, the cards'
sentences (`ledger/cards.py`) and Reconcile's causes (`ledger/workbench.py`). Each string it finds needs a row listing it
in `shown`; each string a row lists must be in one of the ledger/ files under its `where`; a built row with nothing in
`shown` fails. The Release line "Claims register: every shown claim has a row" is red on any of these, on an edited
finding, or when the scan read nothing.

Where it shows: the Gaps page (`#gaps`), `/api/v1/claims`, `docs/CLAIMS.md` (written by `uv run python -m ledger claims`;
a test fails when it is out of date), the Release checklist (the required line above and an informational "Known gaps"
line), and every packet's LIMITATIONS.md (the stub, stale and planned claims). After a deploy of the hosted copy, commit,
`railway up`, then `uv run python -m ledger claims --deployed` (refused on a dirty tree; it records the commit, the
release and which backing tests exist, since the image ships no tests/) and commit `claims/hosted.json`.

## 3. Done when

A ticket is done when:

- each pre-mortem answer has its test, and the tests pass (`LEDGER_SKIP_GOLDEN=1 uv run python -m unittest -q`);
- `uv run python -m ledger golden --check` is equal, or the change of expectation is its own commit with the reason;
- every claim the change adds or changes has its register row, with the tests that back it;
- every review finding not fixed in the ticket is a line in `claims/findings.jsonl`, never only in chat;
- `ledger test` has run on the change, so reports/tests.json names the skipped tests the register reads;
- `docs/CLAIMS.md` is regenerated (`uv run python -m ledger claims`), and the commit message says what was done and what is left open.

## Builder brief (copy into the ticket)

```
Ticket: <id and title>
Why: <the owner's words>
Change: <what to build, where>

Pre-mortem (before code). For each pattern, how this change could hit it, or why it cannot:
 1 label standing in for a check:
 2 vacuous pass:
 3 one decision closing other items:
 4 two consumers disagreeing:
 5 degenerate cases:
 6 late or concurrent writes:
 7 wording that claims more than the check proves:
 8 stale input that looks fresh:

Done when:
 - one test per answer above, named here: <tests.module.Class.test_...>
 - claims/claims.yaml: the rows this changes or adds, with backed_by; docs/CLAIMS.md regenerated
 - claims/findings.jsonl: every finding left open
 - unit tests and golden --check green; commit message says what was done

Reply with: commits, test counts, golden result, the pre-mortem with each test, the register rows touched, the
findings added, anything left undone.
```

## Reviewer brief

```
Review <branch> for <ticket>. Read docs/BUILD.md first.

1. Walk the eight patterns against the diff yourself, not against the builder's list. For each: does the change hit
   it, and does a test fail when it does? Plant the fault where you can (change one line, run the test).
2. Read every claim the change makes on a page, in the API or in the docs. Does the check behind it prove that much?
   Is the claim in claims/claims.yaml, with tests that exist and say what the claim says?
3. Check the inputs are fresh: run against the current database and the current code (restart a running server).
4. Every finding you do not fix: append it to claims/findings.jsonl (source "<ticket> review"), with its claim and
   severity. A finding that is only in your reply is lost.

Reply with: findings by severity (high, medium, low), each with file:line and the pattern number, which you appended to
findings.jsonl, and a verdict: merge, merge after fixes, or rework.
```
