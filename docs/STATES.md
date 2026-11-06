# The implicit state machines

This is the inventory of every implicit state machine in the code (audited at commit 16ddcfb), and of every UI field
born from one. Most defects found in review were state-machine bugs in disguise: "not looked up" read as "looked up, nothing
there"; "unverified" gold read as "pass"; no "stale" state for the EDGAR check; a run's output overwriting a person's
decision; two items sharing one resolution slot; a rejected mapping coming back as current; a release signed and
published while the hosted copy stayed stale. Each machine below lists its states (with the code that produces them),
its transitions (trigger, who may cause it, which are forbidden and whether code enforces that), the page words and API
fields each state produces, and its risks. `ledger/core/states.py` declares the ones that reach a page (`states.MACHINES`), among them row (M1, the
verification words), ladder (M1b), check (M1a), mapping (M5), crop (M14), gold (M7), line (M9) and edgar (M12), each with
its states (unknown, stale and missing named, never folded into a good one), transitions, the one deciding function and
the page word; pages read the words from `/pages/_states.js`, the claims scan from `states.words()`, agents from
`/api/v1/states`; `tests/test_states.py` holds the three test kinds. The rest of the last section is still a proposal. The top risks are findings in `claims/findings.jsonl` (F14 to F30). Every claim was traced in code or data, read-only.
Counts at the audit: `values` labels agree 1003, not_extracted 119, definition_gap 66, not_reported 13, unresolved 10,
no_reference 7; `facts` labels no_reference 2800, agree 1742, unresolved 93 (no other label occurs on facts);
`decisions/decisions.jsonl` 26 lines, all `accept`, 14 by "Kenny Geiler", 12 by "Claude Code, for Kenny Geiler to
confirm", none with `author_kind`; `decisions/resolutions.jsonl` 6 lines; `mapping_proposals.jsonl` 5 `proposed`;
`claims/hosted.json` does not exist.

---

## M1. A dataset row's verification state (`status.state`, the one definition of open)

**States.** `status.STATES = ("checked", "explained", "open", "blocked")` (status.py:48), produced only in `_state`
(status.py:133-155). Blocked: a person's `blocks` (136-137), or a `block`-severity rule (138-139). Checked: `check` in
`CHECKS` (xbrl, quote, located, gate, mapping) or an answer key, which is `esef:`, `source:`, `rule:*_tie`, `actual:`
or `reading:` (140-143). Open: a person's `fix` (144-145). Explained, in order: an `accept`/`explain` resolution
(146-147), a definition (148-149), an info rule or guard (150-151), or the labels `not_reported`/`no_reference` (152-153).
Anything else is open (154-155). Derived: `keys`/`key` (status.py:112-116); `is_open` = open or blocked (196-198).
Per kind: `of_value` (202-223; `not_reported` explained only when `ref.looked_up` and `reference is None`, 211-214;
`not_extracted` open by `label:not_extracted`, 221-222); `of_fact` (229-251, the ladder: readings that differ are open by
`rule:fact_readings_differ`; then a tie is checked by `rule:<id>_tie`, a second reading by `reading:<acc>`, else the label
explains, `no_reference`; `unresolved` plus a restatement is the `restated_between_filings` guard); `of_exception` (254-275); `of_mapping`
(180-189). Proof applies them per stage in `proof.company` (proof.py:75-205).

**Missing or folded states.**
- "Not looked up". For values it folds into open by `label:not_reported` (correct). For facts it is its own state
  (F17): `ties.instance` is the one reading of a filing's instance (the distilled facts or the stored XML, memoised per
  file version; loaded, absent or unreadable) for the ladder, the ties, Proof's lookup marker and the company's own tag
  (`filertag.instance`). `ties.ladder` records each fact's state, a fact it did not see reads absent, and
  `of_fact(..., looked_up="absent"|"unreadable")` makes an untagged fact that no tie or second reading
  checks open by `label:not_looked_up`, ladder rung `not_looked_up`, word "XBRL instance not loaded", taxonomy check
  `not_checked` / `label:not_looked_up`, Proof needs "XBRL instance" (the item says "XBRL instance unreadable" when the
  file does not parse). Before, it read "Unverified · citation only", the
  same as an instance that tags nothing. `instance_totals` reads a stored instance XML whose facts were never distilled
  (`dimensions.parse_instance`, writes nothing), so the tie is tried offline; nothing is fetched. On the six every
  filing's instance is on disk, so no fact reads it today. Locally 294 filings outside the six have only the XML: the
  first read ever parses them (about 7 s) and keeps the parsed facts in `data/cache/instances/` (untracked, keyed by the
  XML's mtime and size, never under the shared data/raw); a new process reads them from there (under 1 s). The hosted copy has the distilled
  facts of the six only (fixtures/data/raw), so a fact of another company reads "XBRL instance not loaded" there.
- A resolution whose item changed, or whose item is gone, counts nowhere (F15, `resolutions.index`): the row reads open on
  every page, as on Reconcile.
- "to confirm" is a string only: Reconcile gives it to run-written resolutions (workbench.py:167), and mappings carry it as
  `by=label:to_confirm` with state `open`. It is not in `STATES`.

**Transitions.** The state is computed, not stored. Its inputs change by: a reconcile label (run: reconcile.py:76,89-97;
notes.py:151), the exception set (`ledger rules`, run), a resolution line (M2), the definitions file
(judgement.write_definition, person; or a hand edit by anyone), an `explains` rule (judgement.write_rule, person), a mapping
confirmation (M5), the ladder inputs (readings, ties, instances on disk).
Forbidden, and whether enforced:
- `not_reported` → explained without a lookup: **enforced** for values (status.py:211); **not enforced** for facts'
  `no_reference` (status.py:247).
- A run-written resolution → explained: **not enforced**. `_res` (status.py:105-109) ignores the author, and `latest()`
  returns a run line when no person line shares its key and hash (resolutions.py:106-126). Only `evidence_gap`
  (status.py:354-357) refuses it, and that runs in tests only.
- A changed item staying explained: **enforced everywhere** (F15, F1). Proof, the Release lines, the read API's
  `status`, the Grid, the taxonomy rows and gold read `resolutions.index(con, tickers)`: the queue items of every
  company with a live resolution (`ledger/review/queue.py` `queue_items`, the producer Reconcile lists, built once per
  stamp by `queue.items_for`) and `by_row(items=…, tickers=…)` over them, so a resolution counts only on the item, key
  and hash, it was written for; one whose item is gone closes nothing. Reconcile passes `flow["items"]` (every item, the
  30-row cut on changed facts is display only). A queue that cannot be built raises `resolutions.Unmatched`: a 503
  "Resolutions not matched · queue not built" on a page, a stopped command, never a quiet reopen. A `fix` on one item
  of a row with an undecided sibling is not the row's status either. `tests/test_one_resolution_rule.py`.
- One decision closing a sibling item: **enforced everywhere**. `_parse` maps `fact_differs` and `fact_changed` to the same
  `facts` row, and `finding_unconfirmed` (non-note) and `blocked` to the same `values` row; with the items, a row with
  an item no current resolution covers is left out of the index, so accepting "fact changed since release" no longer
  explains a fact that still differs from its tag.
- A definition written by a non-person: `definitions.load` needs only a non-empty `by` (definitions.py:22-24), and
  `evidence_gap` checks only that the definition exists (status.py:345-346): **not enforced**. Explains rules are (rules.py:478-479).

**UI fields.**
- Proof board cell counts and the `open` badge, title "open: needs a rule or a definition (blocked counted in)"
  (proof.js:10-14); per company `proven` / `N open` (proof.js:33); legend words checked · explained · open (proof.js:26,34).
- Trail tones from `cards._how` (cards.py:65-112) through `TRAIL_TONE` (trail.js:16): ok "Verified", corroborated
  "Corroborated", info "Unverified", wait "Needs review", bad "Needs review".
- Card sentences (cards.py:72-111): "Proposed category. Review in Reconcile.", "In SEC XBRL, not extracted. Re-read
  required.", "Readings differ: …", "Does not tie to the reported total…", "Matches SEC XBRL: …", "Group sums to reported
  total…", "Confirmed in N filings", "Quote matches source", "Income statement and cash-flow statement located", "No
  blocking items", "Confirmed: <member>", "No external source. Citation verified only.", "Not reported (none in SEC
  XBRL)", "Definition differs from SEC XBRL…", "Reviewer decision: …", "Rule: …".
- Trail stage summary `N verified · N corroborated · N unverified` (trail.js:93), where unverified is `st.explained`;
  tally "N to review" / "complete" (trail.js:98); header "Proven" / "N to review" (trail.js:52).
- Trail status tile (cards.py:267-273): "N XBRL", "N tie to totals", "N confirmed in 2 filings", "N citation only"
  (= every explained figure, cards.py:272), "N to review", "N quotes verified".
- Reconcile `STATE_BADGE`/`STATE_HELP` checked, explained, open, blocked, 'to confirm' (reconcile.js:13-14); header "N to
  confirm, N open, N blocked, N explained" (reconcile.js:67).
- API `/api/v1/proof[/T]` fields `state`, `by`, `key`, `keys`, `proven`, `open`.
- Taxonomy `check`/`check_method` (taxonomy.py:114-132, 209-211; ties.check_columns, ties.py:173-182), vocabulary agree,
  corroborated, no_reference, explained, differs, not_extracted, unmapped, to_confirm, verbatim.
- Release lines "Open items in scope" and "Blocked items in scope" (checklist.py:388-389).

UI words with more than one state:
- "Needs review" = open and blocked (trail.js:16).
- "Unverified" / "citation only" = every kind of explanation: label, definition, a person's resolution, an info rule
  (trail.js:93; cards.py:272). "Reviewer decision" is tone info, so it reads "Unverified".
- "Verified" = xbrl, quote, located, gate, mapping (F10).
- Taxonomy `differs` = every open or blocked fact (ties.py:182).
- "proven" has three meanings (see "Next tier" below).

States with no word: blocked has none on the trail; "not looked up" for a fact has none anywhere.

**Risks.**
- [HIGH] R1: the T80 evidence walk (`proof.unevidenced`, proof.py:345-356) is called only in tests/test_status.py:441,
  against frozen fixtures. No page, release line or CLI runs it on live data.
- [HIGH] Facts conflate "instance not loaded" with "nothing tagged" (status.py:247-248; ties.py:194-195,216-217).
- [HIGH] No hash expiry outside Reconcile (resolutions.py:202-210); related to F1, and not closed by the next rules run.
- [HIGH] A shared row slot on Proof (resolutions.py:176-184).
- [MED] A run-written `accept` reads explained on Proof and the API (status.py:105-109); gate G6 still refuses the release.
- [MED] Definitions need no person on config.PEOPLE (definitions.py:22-24; status.py:345-346).

## M1a. A value's reconcile label (`values.label`, `values.basis`)

**States.** All in reconcile.py: `agree` (89), `unresolved` (89), `definition_gap` (90-97), `no_reference` (89),
`not_reported` (76, and 86 for opex < 0), `not_extracted` (76); basis `restated` / `as_reported` (98).
There is no "XBRL not fetched" state: `reference.get(...) is None` gives `no_reference` or `not_reported` whether the
reference loaded or not. Proof patches it with `looked = bool(xref)` (proof.py:104), per ticker, not per cell.

**Transitions.** Only `ledger reconcile` (run) sets labels. A definition change applies only at the next reconcile, so
until then `definition_gap` can name a definition that no longer exists (only the test-only `evidence_gap` sees it).

**UI.**
- `CHECK` (_shared.js:103): "agrees with XBRL", "definition gap, explained", "differs from XBRL", "no tagged
  counterpart", "not reported"; no `not_extracted`.
- data.js marks (data.js:61-66): agree ✓ "agrees with the SEC's XBRL", unresolved ≠, definition_gap ✓, **anything else ✓
  "checked, no tagged counterpart to agree with"**.
- Reconcile `checkBadge` (reconcile.js:37): "SEC agrees", "not reported", "no tag", "explained" (definition_gap),
  otherwise "differs from SEC".
- API `check_label`, `flag=differs_from_xbrl` (api.py:68-73).
- `XBRL` map (_shared.js:22, trail.js:22): unresolved = "differs from SEC data, decided by a person", which is false for
  an undecided row. Never rendered, but the claims scan registers it.

**Risks.**
- [HIGH] data.js:62 shows ✓ "checked" for open rows (a fact whose readings differ, `not_reported`), because it reads the raw label.
- [MED] reconcile.js:37 shows "explained", the state's own word, for a label.
- [LOW] The dead `XBRL` map.
- [LOW] hq.py:108-111 counts explained/decided its own way (not rendered).

## M1b. A fact's rung on the ladder (`ties.fact_state`)

**States.** Checked by xbrl, `rule:<id>_tie` or `reading:<acc>`; explained by `label:no_reference`, a resolution or the
`restated_between_filings` guard; open by `rule:fact_readings_differ` or an `unresolved` label; open by
`label:not_looked_up`, "XBRL instance not loaded", when the filing's instance is not on disk (F17). Taxonomy rendering:
`check_columns`. A failed tie is its own warn item on Proof.
The hosted copy ships the `*.facts.json` files: without them every untagged fact there reads "XBRL instance not
loaded" (HANDOFF, "The hosted copy").

**Consumers.** Proof (proof.py:132), Reconcile (workbench.py:143), taxonomy (taxonomy.py:135-141) and `gold.compare`
(gold.py:415) pass the ladder. **`gold_view`'s `live.open` does not** (app.py:297; gold.py:341-345).
**Risk.** [MED] The Proof gold table's "live: open" can disagree with `ledger golden --check` for the same fact.

## M2. A resolution (`decisions/resolutions.jsonl`)

**States** per key: none / `accept` / `explain` / `fix` / `blocks` (resolutions.py:30). Word map `STATUS`: accepted,
explained, fix_pending, blocks (76). Orthogonal:
- `author_kind` person/run (85; legacy lines read through `by_person`/`by_run`, 88-104);
- hash current/expired against the live queue item, on every page (`resolutions.index`, F15);
- key live/legacy/stale kind (`is_live` 73-74; `LIVE_KINDS` 37-42).
"Unconfirmed" means the latest line is live and run-written (230-239).

**Transitions.**

| From → to | Trigger | Actor | Guard |
|---|---|---|---|
| any → accept/explain/fix/blocks | `POST /api/resolve`, `/api/resolve/bulk` (app.py:564-570) → `_line` (128-140) | person | **enforced**: state, reason, `is_person`, live key |
| run line → person line (Confirm) | reconcile.js:143 posts the run line's `hash`, reason "confirmed" | person | `latest()` ordered by `at` (106-126) |
| run line supersedes a person line on the same key and hash | any run writer | run | **enforced** (120-125) |
| person on h1, then run on h2 | run | run | allowed: the run line stands, unconfirmed, G6 fails |
| legacy key → migrated copy | `ledger resolutions migrate-keys` (252-279) | code | idempotent, **enforced** (264) |
| a resolution on `value_missing` | — | — | **enforced** (not live) |
| `accept` on `new_filing` (an unread filing becomes explained and leaves the queue) | `/api/resolve` | person | **not enforced** (LIVE_KINDS includes it, 42) |
| a hash that is not the item's current one | `/api/resolve` | person | **not enforced** |
| a key not in the current queue | `/api/resolve` | person | **not enforced** (key shape only, 135-136) |
| an edit or deletion (append-only) | file edit | anyone | **enforced at the Release line** (F30): `claims.append_only_logs` checks every first-parent commit, and every side-branch commit since 2026-11-05, of findings.jsonl, decisions.jsonl, resolutions.jsonl, mapping_proposals.jsonl and the archive files; only a resolution whose key is no longer live may leave, into `decisions/archive/`, byte for byte. The Claims register line is red on an edit |
| a run-written line | no writer in code sets `author_kind="run"` | agent editing the file | a hand-appended `author_kind: person` line by "Kenny Geiler" is a person line |

**UI.** Reconcile "<Accept|Explain|Fix|Blocks> by <by>, <date>" (reconcile.js:94; RES_LABEL/RES_HELP/RES_BADGE 9-11).
The to-confirm group "To confirm: a decision a run made, for Kenny Geiler to confirm or overturn" (workbench.py:167),
with buttons "Confirm <state>" and "Overturn" (reconcile.js:140-148). data.js badges fix/ok/expl/block (data.js:67).
API `status` (api.py:69,72,172). Release gate G6, labelled Proposed, one detail row per key with its page (checklist.py
`g6_detail`, `g6_link`). Card "Reviewer
decision: …" (cards.py:109). The packet README says `status` is "empty, confirmed, overridden or rejected"
(release.py:336): **wrong vocabulary**. API `status` "accepted" can come from a run line (no author filter).

**Risks.**
- [HIGH] No expiry outside Reconcile.
- [HIGH] The signer box defaults to "Kenny Geiler" (_shared.js:30), so every POST from a browser, an agent-driven one
  included, is `author_kind=person` (auth is T6).
- [MED] `new_filing` can be accepted.
- [MED] The hash is not checked against the queue.
- [MED] Append-only is unchecked.
- [MED] Wrong vocabulary in the packet README.

## M3. A review decision on an exception (`decisions/decisions.jsonl`)

**States** per exception: none / `accept` / `override` (with a value) / `reject` (store.py:28). A decision is current
when it is the latest line by **file order** (review.py:16-20) and its `input_hash` equals the exception's (review.py:26).
There is no author field: `decide` writes `reviewer` = any string (review.py:30-40; CLI `ledger review … decide --by`,
cli/review.py:28). There is no `at` ordering.

**Transitions.** Undecided → accept/override/reject through the CLI only (no app route; the docstring at app.py:5-6 is
out of date). A hash change makes it undecided again. Forbidden-but-unenforced: (1) a run or agent deciding, since nothing
checks `reviewer` (review.py:31); (2) a decision closing a **block**, allowed for anyone; (3) ordering by `decided_at`.

**Effects.** `open_items` drops a decided exception from Proof entirely (`decided`, proof.py:112,115,140,195), from gate
G4 (release.gates) and from hq questions and findings, so from the Reconcile queue (hq.py:48,145). `review.apply`
overrides or blanks released values (review.py:43-54; checklist.py:128). Only `proof.missing_from_dataset` asks whether
a person decided (proof.py:361-363,412).
**Verified in the data:** 12 current `accept` decisions by "Claude Code, for Kenny Geiler to confirm" close **block**
exceptions (`xbrl_reconcile` ×10, `statement_tie` ×2) for FCX, HUT, LITE, NRG, SYM, TLN and VST. They are outside SCOPE
at the audit; inside it they would pass G4 and vanish from Proof. G6 does not count them; it reads resolutions only.

**Since F14 (branch `trust`).** `decide` refuses a decision with no author and writes `author_kind`, which every caller
names (`ledger review … decide … --as person|run`, required; person only for a name on config.PEOPLE). `review.closes`: a current decision
closes a warn finding, and a block finding only when a person made it (`review.by_person`: `author_kind`, or for a line
before the field the resolutions rule, a name on config.PEOPLE with no "to confirm"). A run's decision on a block is
`review.proposed`: open under G4, a G6 item `decisions|<ticker>|<exception id>`, Proposed on Proof (release stage, "to
confirm") and on Reconcile's blocks group, and `apply` ignores its override or reject. On a block finding a run's decision
never supersedes a person's on the same input hash; warn and info findings keep the newest line, as before. The 12 accepts above now read Proposed for their seven companies; no line was rewritten.
Since F-TR1 a person also decides one from Reconcile: Confirm or Overturn on the Proposed decision card, `POST
/api/decision` → `review.person_decides` (the proposal standing must be the one the page showed, by decision_id, and the
finding's input hash the page's; else 409) → `decide(..., author_kind="person")`.

**UI.** `/api/company` `status` "note" / "open" / "decided", and `decision {kind, reason, reviewer, decided_at}`
(app.py:84-85). Values change silently in the packet.
**Risks.**
- [HIGH] A run decision closes blocks, with no person check and no G6.
- [MED] Latest is by file order.
- Append-only: checked (F30, above).

## M4. A Reconcile queue item (`app._flow`)

**States.** `q.state` (app.py:227-248): `new` (new_filing), `blocked`, `moved` (fact_changed), `disagrees`
(fact_differs), `missing` (value_missing), `look` (finding_unconfirmed). A `blocks` resolution forces `blocked`
(254-255); `resolution` is attached only on a matching hash (252-253); `open_` = no resolution or `fix` (258). Workbench
rows carry the M1 state (workbench.py:130-151,224), plus two pseudo-causes: `to_confirm` (`state "to confirm"`,
**`open: False`**, workbench.py:167-168) and `asset_types` (M5).

**Staleness.** The `_FLOW` cache stamp (app.py:168-171) covers the DB, resolutions.jsonl, releases/,
data/companies.json and reports/evidence. It does **not** cover decisions.jsonl, data/watch.json, rules/, definitions/,
taxonomy/*.yaml, mapping_proposals.jsonl or gold/.

**UI.**
- `CAUSES` (workbench.py:12-13).
- `CAUSE_ORDER` (reconcile.js:4) **lacks `value_missing`**: it is missing from the Cause filter (62,71) and sorts first.
- "show N resolved" counts checked rows nobody resolved (57,75).
- The header's "N to confirm" counts run resolutions only (workbench.py:282); the Release line also counts unconfirmed
  mappings (checklist.py:399).

**Risks.** [MED] The cache stamp misses inputs. [MED] to-confirm rows are `open: False` while the release refuses.
[LOW] Two "to confirm" counts. [LOW] `value_missing` is missing from the filter.

## M5. An asset-type mapping (`taxonomy/asset_types.yaml` + `decisions/mapping_proposals.jsonl`)

**States.**
- Entry (`status.of_mapping`, status.py:180-189; `taxonomy.unmapped` / `to_confirm`, taxonomy.py:256-275): unmapped is
  open; to_confirm (no person's `confirmed_by`) is open by `label:to_confirm`; confirmed is checked.
- Log (`mapper.by_name`, mapper.py:74-111): `proposal`, `rejected[]`, `reproposed[]` (never current), `late[]` (after an
  approval), `approved`. "Undone" is inferred when an approved name is unmapped or unconfirmed again (105-106).
- `filer`: None means "not checked"; [] means nothing tagged; or ambiguous (476-517).
- A proposal of `"none"` is allowed (31,221).

**Transitions.**

| Transition | Trigger | Actor | Guard |
|---|---|---|---|
| unmapped → proposed | `ledger mapper T` → `propose` (232-236) | run | output validated (197-229) |
| proposed/unmapped → confirmed | `POST /api/mapping` → `approve` (268-329) | person | `person()` (256-265); member on the list; one-entry edit under a lock (384-415) |
| to_confirm → confirmed / replaced | approve (296-305) | person | enforced |
| confirmed → anything via a route | approve / reject | person | **enforced** refusal (129-130, 290-291) |
| to_confirm → unmapped, plus a rejected line | `POST /api/mapping/reject` (114-138) | person | **no person check**: only a non-empty `by` (119-120) |
| a rejected member re-proposed → current | — | run | **enforced** never current (95-96,110) |
| confirmed → undone | hand edit of the yaml | anyone | **not logged, not enforced** |
| unmapped → confirmed by an agent writing `confirmed_by: Kenny Geiler` | file edit | agent | **not enforced** |

**UI.** Reconcile asset rows: badge 'to confirm' (reconcile.js:96), "no proposal yet", "Re-proposed after rejection: …"
(308), "Rejected before: …" (307), filer "not checked: the filer's XBRL instance is not on disk" / "nothing for this
category in its XBRL" / "ambiguous: …" (51), buttons Approve / Reject / Choose another / Map / "Write as …" (reconcile.js mappingCell, mappingActions). Proof "<name>:
<member>, to confirm" / "<name>: no standard asset type" (proof.py:174-176). Cards "Confirmed: <member>", "Proposed
category. Review in Reconcile.", "→ unmapped" (cards.py:72,100,173). Taxonomy `check`, `mapped` (taxonomy.py:87,209-211).
Release: an unmapped name counts on the Needs review line, listed on Proof or not (checklist.py `review_counts`); a
to-confirm entry on gate G6, labelled Proposed (`g6_detail`). Claims
`mappings_confirmed` (claims.py:310-315). One row shows both the badge "open" and the chip "to confirm".
**Risks.** [MED] Reject has no person check. [MED] A hand-confirmed entry looks the same as one confirmed through the route.
[LOW] An unrecorded "undone". [LOW] Approving a `none` proposal fails only with a 400.

## M6. A filing or text through the pipeline

**States.** Listed (watch) → parsed (`runs` outcome ok/failed/skipped, store.py:267; skipped = a 10-K/A with no
statements, cli/ingest.py:82) → located / amendment guard / "a statement table not located" (proof.py:90-95) → task
packed → output (`_run.task_sha`) → loaded (ok) / failed (`*_failed` exception, outcome failed) / stale (refused at load).

**Guards.** extract, notes and aispend `--load` refuse a stale output (cli/extract.py:103; cli/notes.py:114;
cli/aispend.py:114). **`agent.stale` loads an output with no task_sha** (agent.py:116-118), while `--run` treats it as
stale (cli/extract.py:66). **`ledger projects --load` has no task_sha check** (cli/projects.py:95-105).
**UI.** hq pipeline steps "Find 10-Ks", "Locate statements", "Agent reads", "Re-read on filing", "Match the SEC's data",
"Fault test" (hq.py:81-91); Proof ingest failure items (proof.py:96-98); card "Income statement and cash-flow statement located".
**Risks.** [MED] Projects outputs load stale. [MED] An output with no fingerprint loads. [LOW] G1 counts only
`extraction_failed`, while Proof counts all four failure kinds (proof.py:32).

## M7. A gold item (`gold/<T>.json`)

**States.** `verdict` ∈ {null, right, wrong, cant_say} (gold.py:35,39). Against the live tables (`compare`, 352-400):
- right: holds / value changed / row gone / gold has no value;
- wrong: holds / still ships and not open / changed since verdict / row gone / blank;
- cant_say: neutral; no verdict: unverified.
Aggregate `state` is fail, unverified or pass (398). File problems: missing, empty or corrupt (165-189).

**Transitions.** null → verdict, or verdict → another verdict: `POST /api/gold/verdict` → `record` (274-296; person
**enforced** at 282; a note for wrong and can't say; a lock). A redraw keeps verdicted items (196-201, 235-258).
Overwriting a verdict leaves no record in the file.
**UI**. `GOLD_WORD` Right / Wrong / Can't say in `GOLD_TONE` colours, "Unchecked"; "Current value
unavailable" / "Removed from dataset" / "Now $X" / "Needs review"; the rate line `goldRate`; the Proof header "Hand check: N of M
checked | pass | N wrong | not run" (`goldState`); each item's cited cell as the trail shows it (M14); the Release Golden note (checklist.py:319-322); `summary_line`
(gold.py:418-426); claims `_gold` (claims.py:247-259).
**Risks.** [MED] `live.open` ignores the ladder (app.py:297). [MED] A "right" whose value changed lacks the "changed
since verdict" wording (gold.py:385-386 against 396). [LOW] No verdict history in the file. [HIGH, via M9] Verdicts
given after the last golden run are not reflected.

## M8. A release (`releases/vX/`, Postgres, the hosted copy)

**States.** Folder: none / same / different / signed / broken (`folder_state`, checklist.py:81-96); an unsigned
folder older than the last signed one is superseded and skipped (`next_version`, 65-78). Signed, with or without
`checklist` (CLI signing records none, cli/signoff.py:26-27). Published: true / false / absent (checklist.py:499-510;
`record`, cli/signoff.py:32-41); in Postgres, `ledger_releases`. Hosted: claims/hosted.json `release` and `commit`
(claims.py:295-307).
On disk: v1.2.0 unsigned; v0.1.0 to v1.7.0 signed through the CLI, with no checklist and no `published`; v1.8.0 signed
with a checklist, published true.

**Transitions.**

| Transition | Trigger | Actor | Guard |
|---|---|---|---|
| none → built | `ledger release` (cli/release.py:21-46), the sign route (checklist.py:493) | person/CLI | required lines green |
| built → signed | `POST /api/release/sign` (app.py:554-563; checklist.py:475-511), `ledger signoff --by` | owner only (HANDOFF rule 6) | **`by` not person-checked** (checklist.py:484, non-empty only; the CLI takes any string); hash enforced |
| signed → re-signed | — | — | **enforced** refusal (cli/signoff.py:18-19) |
| signed → published | the sign route, or `ledger publish` (publish.py:44-56,105) | person | signed and hash-matched |
| published=false → published | `ledger publish` | person | **SIGNOFF.json not updated** (cli/publish.py:25-33 never calls `record`) |
| published → hosted deployed | `railway up` + `ledger claims --deployed` | person | **not part of signing**; only the informational "Known gaps" line (checklist.py:351-353) |
| a signed release's files edited | file edit | anyone | caught at publish (hash) |

**UI.** Release's releases table "<by>, <date>", plus ", not published" only when `published === false`, or "not signed"
(release.js releasesTable), with "To review at signing", "Unmapped at signing", "Companies". The trail's "Last release" (trail.js:83) comes
from `cards.last_release`, **which skips a signed release with no checklist** (cards.py:219). The Release page status
"signed by … · published: …" / "not published: …; the signature stands, run ledger publish" (release.js:43-44). Packet
line notes (checklist.py:438-443). `/api/outputs` `published` (app.py:323).
**Risks.**
- [HIGH] The signer is unchecked.
- [HIGH] A stale hosted copy never blocks signing or publishing (F6 is live).
- [MED] A CLI publish leaves `published: false` behind.
- [MED] An absent `published` has no word.
- [MED] The trail hides releases signed through the CLI.

## M9. A Release checklist line

**States.** `state` ∈ pass / fail / info / not_run; `ok = state == pass`; `required` (checklist.py:268-270). **Stale
folds into info**:
- tests stale (dirty tree or moved HEAD) → info, not required (303-306);
- "commit not compared: no git" → info (297-298);
- tests absent → `not_run`, **not required** (286-287);
- Golden absent → fail, note "not run" (314-315);
- **Golden has no staleness at all**: golden.json carries `at` but no commit (cli/golden.py:37), and `golden_line` ignores both (310-326).

**UI.** `LINE_STATE` "passes" / "fails" / "info" / "not run" (release.js:4); count "—" when not run (59); "yes" /
"informs" (60); the Sign button's reason (34-35). "stale" appears only in the note text.
**Risks.** [HIGH] A release can be signed with tests not run, or run on another commit or a dirty tree. [HIGH] An old
golden run reads green. [MED] No line for EDGAR freshness or the hosted copy.

## M10. A review finding (`claims/findings.jsonl`)

**States.** `FINDING_STATES = ("open", "fixed", "wontfix")` (claims.py:67); the latest line per id by file order
(116-147); later lines may change only `status`/`at` (`MUTABLE`, 70; enforced 140-144); every committed version must be a
prefix (163-180; with git only).
**Transitions.** Any state → any state by an appended line. Not enforced: fixed with no evidence that the fix landed.
**UI.** Gaps page severity, text, claim, ticket; "Append-only log edited" / "Append-only logs: not enforced here"
(every append-only log, F30); Release "Known gaps: … open findings" (checklist.py:351). **Risk.** [LOW]

## M11. A claim (`claims/claims.yaml`, `ledger/release/claims.py`)

**States.** `STATUSES = ("proven", "partial", "stale", "stub", "planned")` (claims.py:63); the worst of the reasons
(`compute`, 348-386). Checks: gold (247-259), EDGAR (262-275; `STALE_HOURS` 48; `clock.age_hours` problems never /
unreadable / no zone / in the future), hosted (295-307), mappings (310-315), golden (318-333); a check that raises is
stale (378).
**UI.** Gaps `CLAIM_STATE` badges, "· declared X" (gaps.js:3,37); counts line (gaps.js:26); Release "Claims register…"
and "Known gaps…" (checklist.py:348-353); docs/CLAIMS.md and LIMITATIONS.md ("checked live only").
**Risks.** [MED] "proven" overloaded. [LOW] Golden is stale only when the file is missing; age is never checked.

## M14. A cited cell's crop

**States.** none (no crop on record, or no extraction on file) · stale (the stored filing, its fingerprint, the citation or the
crop code changed) · not_located (the locator did not find the cited text there; reason kept) · missing (the picture is gone
or not the one written) · located (current). Computed on every read, never stored.
**Who decides.** `crops.state` only. `crops.cells` reads it for a list of extraction ids and `crops.brief` shapes it for a
row; the trail (`cards._cell`), the gold set (`app.gold_view`), Reconcile's cited cell (`workbench.items`, fact_differs) and
`/api/v1/evidence/<id>` (`crops.view`) all go through `cells`. Test: `tests.test_crops.RowEvidence`.
**Transitions.** `ledger evidence --crops` writes located or not_located (`crops.run`, `crops.merge`: an older run never
replaces a newer one); any change to the filing, the citation or the code makes it stale; a changed picture makes it missing.
**UI.** `_shared.js` `CROP_STATE`: Cell located · Cell not located (· reason) · Crop out of date · Crop file missing · No crop.
A row shows the picture only when located (`citeCell`, the thumbnail zoomed on the red box, full size on click), else the
state word, never a blank. Open goes to `/filing/<accession>?t=&row=&col=&cell=` (the in-app viewer); sec.gov is the second link.
The picture route `/evidence/crops/<name>` serves a file only while `crops.state` calls its entry located (the record is
indexed by picture name, `crops.extraction_of`). The viewer's banner is its own live find on the served page ("Found on
this page" / "Not found on this page"), not this state. The Dataset drawer shows the same crop; the older re-read
screenshots are no longer served.

## M17. A gold item's group (review-fixes, 2 Nov 2026)

**States.** no_counterpart (no_reference, not_reported, or an agree claim with no XBRL value) · definition (definition_gap,
unresolved) · not_extracted · not_reconciled (no label, a label off the list, or the live row gone; the absent state) ·
calculated (agree, and its calculation from several cells exists and holds) · xbrl (agree). Words: No SEC counterpart ·
Definition differs · Not extracted · Not reconciled · Calculated · Matches SEC XBRL (`states.GOLD_GROUP`), in that order.
**Who decides.** `gold.group(item, calc)`. `gold.live_groups` gives each item its group from the claim at the draw and
from the live tables (label, XBRL value, the live calculation); an item counts under its live group in `gold.rates`
(per group and overall: right / wrong / can't say / unchecked, Wilson 95% when n > 0; headline no_counterpart) and the
Proof page flags a move ("Group changed since draw: was X, now Y", `gold.group_note`); the verdict stays. `/api/v1/gold`,
the Proof page and `ledger gold --status` read `rates`. With the database busy the groups are the claims' and the page
says "Groups as drawn". Tests: `tests.test_calc.Groups`.
**Transitions.** Any group to any other, by a change in the live tables; never by a verdict.

## M18. A calculated figure's cross-check (review-fixes, 2 Nov 2026)

**States.** matches (within half a rounding unit per input) · explained (the filing's own total differs by exactly one
formula input, sign-aware, and no other line: "Filing's total includes cost of sales · $326,288M"; neutral) · differs
("differs by $X", naming the line only when exactly one line, sign-aware, is that amount) · none ("No total to compare":
no "Total operating expenses" row in that table and column, or no XBRL value).
**Who decides.** `calc.state`, inside `calc.calculation`; SEC XBRL is compared with the inputs only, never a table row.
`calc.for_ticker` feeds the trail's card and the gold set (through `gold.live_groups`). Tests: `tests.test_calc.Calc`.
**UI.** `calcBlock` (_shared.js): "Calculated: revenue − cost of revenue − operating income = $X", the arithmetic on the
real inputs (to the dollar when rounded terms would not add up), each cross-check in its tone; each crop labelled with
its role (Revenue / Cost of revenue / Operating income).

## M19. A company's filing state (F-BF15, 5 Nov 2026)

**States.** filed ("Filings read": at least one filing read) · unfiled ("No filings yet": in `config.tracked()`, no filing
read) · unknown ("Unknown company": not followed, no filing read). Absent input is unknown.
**Who decides.** `states.company(tracked, documents)`, read by `proof.company` (its `filing_state`; `proven` needs filed) and
the trail route (`/api/v1/proof/<ticker>`: 404 with the unknown word). A database that cannot be read is a 503, never unknown.
**UI.** The trail's head and its release card show the word instead of Proven / Ready for release; an unknown ticker's
trail shows only the word.

## M20. Whether a reading answered the current task (F25, 5 Nov 2026)

**States.** current ("Reading current": its `_run.task_sha` is the current task's) · stale ("Reading answered an older
task") · unfingerprinted ("Reading not fingerprinted": no `_run.task_sha`). Absent input is unfingerprinted.
**Who decides.** `agent.reading_state(obj, task_text)`. The four loaders (extract, notes, aispend, projects `--load`)
refuse a stale output as their `*_failed` item (projects since F25). An unfingerprinted output still loads (its rows stand;
nothing is re-run by the check), and `agent.unfingerprinted(con, tickers)` lists every one on disk: Proof's ingest stage
shows each open by `label:unfingerprinted`, needs "Re-read (--run)", and Reconcile lists it under "Reading not
fingerprinted" (kind `reading_unfingerprinted`, not a live resolution kind: no decision closes it). The two pages count
it the same (Needs review). `<step> --run` re-asks it and writes the fingerprint.
**Today.** 4 statement outputs (CRWV one, ORCL three), none on the six: the nine MSFT, NVDA and APLD ones were re-read on 2026-11-05.

## M12. Freshness of the monitoring inputs

| Input | Fresh / stale rule | Read where | Not checked where |
|---|---|---|---|
| data/watch.json `checked_at` | ≤ 48 h (clock.age_hours) | trail (cards.status_line; trail.js "SEC checked Nh ago", "Nd ago · out of date", "SEC never checked", "SEC check failed"); claims `_edgar` | **the Reconcile `new_filing` items and hq** use `watch.new` with no age (app.py:221; hq.py:192); `watch.new` is never reconciled with filings read since, only `watch --run` re-checks (cli/watch.py:38-41); "N new filings not read" (trail.js) lingers; no release line |
| reports/golden.json | none (no commit) | — | the Golden line; the Proof header "Regression test: pass · <date>" (proof.js) |
| reports/tests.json | HEAD and dirty tree | the Test run line (checklist.py:276-307) | stale does not block |
| claims/hosted.json | release and commit | claims `_hosted` | the release gate (M8); absent at the audit |
| `/api/hq` in the browser | — | — | `hqCache` (_shared.js:92) until a reload |
| scope line "data as of <run_at>" (_router.js:36) | — | — | no age, no code version |

**Risks.** [HIGH] A stale watch drives Reconcile's new-filing items and "not ingested" (F7 is live: last check 28 Oct).
[HIGH] Golden has no freshness.

## M13. Explains rules and definitions (T36)

**States.** An explains rule: valid (`_check_explains`, rules.py:463-486) or a load error, in which case Proof shows
"rules/ does not load" open (proof.py:197-198) and no rule explains anything. A definition: valid or a load error
(definitions.py:17-31), with an optional `periods` scope (`_applies`, 34-39).
**Transitions.** `POST /api/judgement` → `encode` (judgement.py:131-146; person enforced; live and offered), or a hand
edit. Rules re-check `by` at load (rules.py:478); **definitions do not** (definitions.py:22).
**UI.** "Make this a rule" / "Make this a definition" (reconcile.js:212-218); "Definition differs from SEC XBRL: …",
"Rule: …" (cards.py:105-111); the Rules page kinds (rules.js:80). **Risk.** [MED] A non-person's definition explains values.

## M14. The local app server process

**States (implicit).** Python is loaded once at `serve` (app.py:625), but `app.html` (396) and `pages/*.js` (450-453) are
read on every request, so **new JS can run against old Python**. Caches: `_FLOW` (165-181; the stamp gaps are in M4) and
`_INSTANCES` (workbench.py:42-51). `READONLY` (367). There is no state for "the server runs code older than HEAD": no
start commit, no start time, no version endpoint. `/api/hq` returns only `readonly`, and the scope line says "local" or
"read-only copy" (_router.js:36).
**Risk.** [HIGH] The stale-server case has no state, no word and no check (BUILD.md pattern 8).

## M15. A point-in-time vintage check

**States.** `vintage_check` is the label, or `"unchecked"` for an older vintage (pit.py:111); an as-of taxonomy `check`
is the check, or **`"not_checked"`** (pit.py:138). Two words for one state. **UI:** `/api/v1/values?as_of`,
`/api/v1/taxonomy?as_of`, `AS_OF_NOTE` (api.py:19-20). **Risk.** [LOW]

## M16. A run started from the app (dormant)

`job()` steps done / running / waiting, and `exit` (app.py:341-364). A killed process with a stale progress.json reads
"not running, exit None", with no "died" state. No page renders `/api/job`. [LOW]

---

## Summary

Counts are of the entries listed above.

| Machine | States | Transitions listed | Forbidden, unenforced | UI fields listed |
|---|---|---|---|---|
| M1 row state | 4 (+ "to confirm") | 7 input kinds | 5 | 30 |
| M1a value label | 6 + 2 basis | 1 | 1 | 14 |
| M1b fact ladder | 7 rungs | 1 | 1 | 6 |
| M2 resolution | 5 × author × hash × key | 11 | 5 | 9 |
| M3 review decision | 4 × current/expired | 3 | 3 | 3 |
| M4 queue item | 6 + 2 pseudo | 4 | 1 | 6 |
| M5 mapping | 3 entry + 5 log + filer 3 | 8 | 3 | 14 |
| M6 pipeline | ~8 | 4 | 2 | 9 |
| M7 gold item | 4 verdicts + 9 outcomes | 3 | 1 | 10 |
| M8 release | 5 folder + signed ± checklist + 3 publish + hosted | 7 | 4 | 8 |
| M9 checklist line | 4 (stale folded into info) | 1 | 2 | 6 |
| M10 finding | 3 | 1 | 1 | 5 |
| M11 claim | 5 | computed | 0 | 5 |
| M12 freshness | fresh/stale × 5 inputs | — | 3 | 7 |
| M13 rule/definition | 2 × 2 | 2 | 1 | 4 |
| M14 server | loaded/stale (missing) | 1 | 1 | 0 |
| M15 vintage | 2 (two words) | — | 0 | 2 |
| M16 job | 3 + exit | — | 0 | 0 |

## Top 10 risks, ranked (findings F14 to F23)

1. **[HIGH] M3:** Review decisions have no author check and close **block** exceptions, dropping them from Proof, gate
   G4 and the queue. 12 current block "accepts" are by "Claude Code, for Kenny Geiler to confirm"; there is no G6 for them.
2. **[HIGH] M1/M2:** A changed item's resolution counts everywhere but Reconcile (resolutions.py:202-210), and two queue
   items share one row slot there (176-184).
3. **[HIGH] M1:** The T80 evidence walk runs only in a test on frozen fixtures (tests/test_status.py:441). Closed by F16: a required Release line runs it on the live tables.
4. **[HIGH] M1b:** A fact whose instance was never loaded reads "explained, citation only" (status.py:247-248; ties.py:194-195,216-217).
5. **[HIGH] M8:** The signer is not checked (checklist.py:484; cli/signoff.py:47), and the page pre-fills "Kenny Geiler"
   (_shared.js:30) for every decision, verdict and mapping. Closed by F18: no default name; signoff and every write check config.PEOPLE.
6. **[HIGH] M8/M12:** A release signs and publishes while the hosted copy is stale or unrecorded.
7. **[HIGH] M9:** Tests not run or stale do not block; golden carries no commit, so an old golden reads green and later
   verdicts are not reflected. Closed by F20: both lines require the commit being signed and a clean tree; the hand check is live.
8. **[HIGH] M14:** A stale server has no state; the `_FLOW` stamp misses decisions.jsonl, watch.json, rules/,
   definitions/ and taxonomy/. Closed by F21: the stamp covers them; /api/hq compares running and checkout code.
9. **[HIGH] M1a:** The data page shows ✓ "checked" for open rows; the trail's "Needs review" covers open and blocked,
   and its "Unverified" / "citation only" covers every kind of explanation.
10. **[MED-HIGH] M12/M4:** watch.json drives Reconcile's new-filing items with no age check and no reconciliation
    against filings read since, and a new filing can be "accepted" away unread.

Next tier (F24 to F30):
- A CLI publish leaves `published: false`.
- `projects --load` has no task_sha check.
- `gold_view` reads facts without the ladder.
- The packet README's `status` vocabulary is wrong.
- "proven" means three things: `config.PROVEN` membership (api.py:67, release.py:335), Proof's nothing-open, and the
  claim status.
- "unchecked" and "not_checked" name one state.
- resolutions.jsonl, decisions.jsonl and mapping_proposals.jsonl are checked as append-only since F30 (`claims.append_only_logs`).

## Proposed design: declare the machines in code (`ledger/core/states.py`; the machines that reach a page built, the writer hooks and replays below still planned)

```python
@dataclass(frozen=True)
class Machine:
    id: str                        # row, resolution, decision, mapping, gold, release, line, finding, claim, freshness, pipeline, server
    states: dict[str, str]         # name -> meaning; one of kind "unknown" (not looked up / not run) and one "stale", or no_stale_because
    kinds: dict[str, str]          # state -> terminal | open | unknown | stale
    transitions: tuple[Transition, ...]   # (from, to, trigger "module.func", actors frozenset{"person", "run", "code"})
    ui: dict[str, tuple[str, ...]] # state -> every displayed word (page maps, card sentences, line badges, API enum values)
    api_fields: dict[str, str]     # API or CSV field -> the state it carries

def allow(machine: str, frm: str, to: str, actor: str) -> None   # raises IllegalTransition
```

**Writers call `states.allow` before they write:** `resolutions._line`, `review.decide`, `mapper.approve` / `reject` /
`propose`, `gold.record`, `checklist.sign`, `cli/signoff.sign`, `publish.publish`, the findings append, and the loaders'
stale refusal. The actor comes from `status.is_person`, the writer's identity, or code.

**Readers return declared names:** `status._state`, `of_*`, `checklist._line`, `claims.compute` and `folder_state`
return names from the declarations, so no state can appear undeclared.

**States to add:**
- row `stale` (a resolution on a changed hash; F15 closes it as open, no own word); ladder `not_looked_up` is produced (F17);
- line `stale` (its own badge; required lines treat it as fail);
- decision `author_kind`;
- release `deployed` / `hosted_stale`;
- server `stale_code` (record the commit at `serve()`, expose `/api/v1/version`, compare it with HEAD);
- watch `stale`, applied to the queue as well.

**The three test kinds.**

1. **No illegal transitions.** Unit: for every (from, to, actor) not declared, the writer raises; the product is
   generated, so a new state forces a decision. Replay: walk resolutions.jsonl, decisions.jsonl, mapping_proposals.jsonl
   with the yaml, findings.jsonl and the gold verdicts in `at` order through `allow`; an illegal step fails. The replay
   doubles as the append-only check for every log.
2. **No missing unknown or stale states.** Every machine declares an `unknown` and a `stale` state, or says why it has
   none. A matrix test feeds each reader its absent-input cases and asserts the declared unknown or stale state, never
   checked, explained, pass or proven. The cases:
   - no reference_values table, or an empty one for the ticker;
   - no instance file;
   - no gold folder;
   - golden.json missing, or from another commit;
   - watch.json older than 48 h;
   - no hosted.json;
   - a server started on an older commit;
   - an output with no task_sha.

   The same suite runs `proof.unevidenced` on the live database for the proven set, behind a new required Release line
   "Every checked or explained row names its evidence".
3. **Every UI field maps to exactly one state.** Extend `claims.scan` (claims.py:412-478), which already reads the label
   maps, toned elements, WATCHED strings, cards.py and workbench `CAUSES`:
   - every scanned string must be in exactly one `Machine.ui[state]`: zero is "state word unregistered", two or more is
     "ambiguous state word" (this catches "Needs review", "Unverified", "info", "explained" and "proven");
   - every declared state has a word, or `hidden: why`;
   - every page label map's keys equal the machine's state set (this catches `CAUSE_ORDER`, `CHECK` and the dead `XBRL` map);
   - API enum fields (`status`, `check`, `vintage_check`, `published`) and `release.COLUMN_DOCS` use the declared vocabulary.

   Claims rows gain `machine:` and `state:`, and `claims.unregistered` reports the new problem kinds.

**The hook.** The new problem kinds turn the required line "Claims register: every shown claim has a row" red, through
`checklist.claims_lines` (checklist.py:329-354). Alternatively, a sibling required line, "State machines: every log replays
legally, every UI word maps to one state, every reader names its unknown state", runs these checks live, not from
tests.json. Add the missing gates as required lines:
- tests stale = fail (built);
- golden commit ≠ HEAD = fail (built, F20: stale, which blocks);
- watch older than 48 h = fail;
- hosted ≠ latest signed = fail after publish, or a "deployed" step in `sign`;
- run-authored current decisions in decisions.jsonl counted in G6 (built, F14).

## Display words (not states)

`ledger/core/states.py` `DISPLAY` declares the words a page says about a row that are not a state of it. They are listed
by `states.words()` with the state words, so the claims scan reads them from states.py and `tests.test_states.Words`
holds each to one owner; the row keeps the state its machine gives it.

| Key | Word | Where it shows | Meaning |
|---|---|---|---|
| restated | Restated | gold item, trail row, evidence page, Reconcile drawer (`ties.restatement` line) | the readings of one fact disagree across filings: every figure as filed, oldest first, and the one the dataset uses |
| superseded | Superseded | under a reading's crop (`ties.mark`) | a figure the dataset does not use |
| source_not_found | Source reading not found | the end of the Restated line, in place of "dataset uses" | never good: no reading from the fact's own filing carries the dataset's figure |
| segment_basis_mixed | Segment basis mixed | the trail card and Reconcile's cause label for the rule's finding | a segment series whose release years come from both sides of a re-segmentation (open until a person decides) |
