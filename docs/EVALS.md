# Evals: how the pipeline grades its own agents

Written 2 Nov 2026 from the code. It maps the pipeline onto a standard evals checklist for AI systems, says what
each part does here, where it lives, and whether it is built, being built, or planned (with its ticket in
[TICKETS.md](TICKETS.md)). The spec for what "proven" means is [PROOF.md](PROOF.md); this file is about how the
agents are measured.

## The idea in four sentences

Agents read filings; code grades every answer; a person decides only what code cannot. No model grades another
model: every check is deterministic, so a score has no variance and can be rerun to the same result. An agent's answers
are frozen as inputs to the golden test, so a change to any parser, rule or loader is measured against the same
answers. Every failure found becomes a named type, a check that catches it, and a frozen fixture, so the same mistake
cannot come back silently.

## The loop

1. An agent reads a filing and answers in JSON, citing the exact cell for every number.
2. Code checks the answer: its shape, each citation against the parsed filing, then the rules and the answer keys.
3. Each row lands in one state: checked, explained, open or blocked (`ledger/status.py`, one function for every page).
4. A person looks only at open rows, and decides by writing a definition, a rule or a resolution.
5. A new kind of failure is written up as a failure type, given a check, and frozen into the golden fixtures.
6. The golden test, the test suite and the release gates refuse any change or release that makes things worse.
7. The scores per agent, the error rates and the cost per company show whether the loop is getting cheaper and better.

## Where each practice lives

| Practice | Here | Status |
|---|---|---|
| Error analysis before metrics | The failure log, then failure classes and a ranked chart | Log built; classes T54 |
| Versioned golden set | `ledger golden`, `fixtures/`, prompts versioned in `agents/prompts/` | Built |
| Synthetic cases along dimensions | `ledger faults`: six kinds of planted error on real extractions | Built |
| Deterministic assertions first | Schema, citation checks, 15 rules, four answer keys, a rendered second read | Built |
| Trajectory and run logs | `runs` table: model, tokens, seconds, attempts per call | Built |
| Score per agent | `ledger/score.py`: counts with their denominators | Built (T49, merged 1 Nov) |
| Confidence intervals | Wilson 95% on every share | Planned (T53) |
| Error rate where no answer key exists | Stratified hand-checked sample, ASML first | Planned (T53) |
| Reliability across runs (pass^k) | Same task run k times per reader | Planned (T60) |
| Paired test before a prompt change | Old and new prompt on the same cells, per field | Planned (T61) |
| Gates in CI | Golden check, `reports/tests.json` (`ledger test`, T30, merged 1 Nov), release gates G1–G6 | Built |
| Live monitoring | `ledger watch` for new filings; decisions expire when their inputs change | Built; reopen on new evidence T57b |
| Cost as a metric | `ledger/cost.py` per company and per agent; person minutes | Agent cost built; person minutes T38 |
| Close the loop | Failure → type → check → fixture → golden freeze | Built |

## Error analysis: the failure log

[INGESTION.md](INGESTION.md) is the open coding: every failure met on real filings, written in free text with the
company, the cause and the fix (units written "(000,000)", a 53-week year, a quarterly table winning over the annual
one, a quarter used as a full year). T54 does the axial coding: `failures.yaml` gives each type a cause class (units,
period, scope, locator, agent misread, document error), how often it happened, the check that catches it, and whether
the agent or the document was at fault. A ranked chart on the Proof page then shows which few causes make up most
errors. A type whose catching check is "none" is a finding in itself: a known way to be wrong that nothing guards.

## The golden set

`ledger/golden.py`. `freeze` copies, for the proven companies, everything the code stages read (parsed tables, texts,
the agents' answers, document rows) into `fixtures/`, and the tables the code makes from them into
`fixtures/expected/`. `check` rebuilds the repo in a temporary folder, runs every code stage with nothing fetched and
no agent asked, and compares every table column by column, row by row.

- Agents are frozen on purpose. Their answers are inputs; the checks on those answers are what is tested. A prompt
  change is measured separately (T61).
- The set is stratified by design, not by convenience: each proven company was chosen for the case it carries
  (`config.PROVEN_WHY`: a category rename, a restatement between filings, segment capex above cash capex, the seller
  side), so rare cases are not drowned by easy ones.
- `--check` runs before any commit that touches a parser, rule, loader, taxonomy or schema. `--freeze` runs only on
  purpose, in its own commit that says why.
- Prompts are versioned and never edited in place: `agents/prompts/<id>@vN.md`, the model pinned in
  `agents/agents.json`, every change logged with who made it. Every score can be traced to the prompt and model that
  produced it.

## The gold set (T82)

Golden is a regression test: it says nothing changed, and it froze the Amazon blanks as expected (docs/DISCIPLINES.md).
`gold/<TICKER>.json` (`ledger/gold.py`) is the correctness test beside it: per proven company about 10 values and 10
facts, stratified by field and year, untagged facts (no XBRL twin) oversampled to 6 of the 10, drawn with the seed
`GOLDEN_SEED|<release version>|<ticker>` so the sample moves between releases. Each item holds the claim (ticker,
field, dimension, period, value, the cited cells with deep link and screenshot) and a person's verdict: right, wrong or
can't say, a note, `by` on `config.PEOPLE`, `at`.

- `ledger gold --draw` writes the files and never overwrites or drops an item that has a verdict.
- Verdicts are given on Proof, Gold set (`POST /api/gold/verdict`, the one writer `gold.record`: lock, temp file,
  os.replace; a name not on `config.PEOPLE` is refused).
- `ledger golden --check` compares every verdict with the tables the run produced: right must still equal the gold
  value (a blank or a missing row fails), wrong must differ or the row be open. Items without a verdict print as
  "unverified: N", never as a pass.
- Error rate: wrong of (right + wrong), with n and a Wilson 95% interval (`gold.error_rate`); can't say is counted
  beside it, not in the denominator.

## Planted errors

`ledger/faults.py` corrupts one real extraction at a time, the way agents misread statements, and records what caught
it. The six kinds are the dimensions: wrong column, stale (comparative) column, wrong row, wrong scale, sign flip,
misread digits. Each fault ends in one outcome: no effect (it never reaches a released value), caught by a rule,
caught only by the XBRL comparison, or escaped (a released value changed and nothing fired). The latest run on the
proven six caught 1,275 of 1,283 planted faults with none escaped; the eight others had no effect on a released value.
Reports are in `reports/<companies>-faults.json`.

## Deterministic checks, in order

1. The task hides the answer key. The reader sees only the statement tables, never an XBRL value or tag name
   (`ledger/extract.py`), so agreement with XBRL means something.
2. Shape. The answer must match its JSON schema (`agents/schemas/`); a broken answer gets one retry with the reason,
   then is recorded as an error, never guessed (`ledger/agent.py`).
3. Citation. Every value names a table, row, column and cell; the cell must exist in the parsed filing and the cell
   times the unit must equal the value (rule `citation_resolves`).
4. Rules. Fifteen rules in `rules/*.yaml`, each with a severity. Block: citation, column matches period, period length,
   sign, statement tie, cost lines summed, XBRL reconcile. Warn: coverage, jump, outlier against own history, row label
   switch, unit from elsewhere in the document. Info: definition note, no 10-K yet, restated.
5. Answer keys. Four kinds, each named on the row (`status.ANSWER_KEYS`): a structured twin (XBRL, ESEF), a second
   source (the earnings release against the 10-K), an arithmetic tie (quarters sum to the year, aligned ≤ eligible ≤
   total), a later truth (the actual against what was planned). They are not equally strong: a twin is independent of
   the reading, while an earnings release comes from the same finance team and can share its error. T56 grades them so
   each row shows its strongest key.
6. A second read on the rendered page. `ledger/evidence.py` opens the 10-K in Chrome as a person sees it, finds the
   cell by its row label and column header on the page, not through the table parser, and boxes it in a screenshot.

There is no model-based grading. Everything above is code a person can read and rerun.

## Scores per agent

`ledger/score.py` (T49) scores each live reader on the companies in scope: how many of its outputs are checked,
explained, open and blocked, how many agree with their structured twin where one exists, and how many planted faults
the checks behind it caught. Every count is shown with what it is out of; the page computes the shares. On the six
today: the statement reader has 70 of 81 rows checked and 70 of 71 agree with XBRL where a tag exists; the notes
reader has 180 checked and 147 explained of 327, with 180 of 185 agreeing with the filing's own tags.

Each agent has a charter in `agents/charters/<id>.md`: what it owns, what it never touches, its input and output
files, its model and tools, its prompt versions, and the checks that judge it.

## Statistics

- Intervals (T53, built for the keyed share). Every share gets a Wilson 95% interval. At 100 cells and 80% correct, the interval is about ±8
  points, so a move from 80% to 83% is not a result. `ledger/stats.py` computes it; `score.twin.interval` carries it per reader and the
  Rules page writes it in text beside the share (reader 70 of 71, 92.4–99.8% on the six). Per field waits on `field` on the trail's items.
- No answer key (T53). For a source with no structured twin (the ASML annual report's EU Taxonomy capex table is
  untagged), a person checks a stratified random sample of cells, oversampling the risky parts (the KPI table, note
  roll-forwards, long tables). The error rate is reported with its n and interval. This is how error is measured on
  the documents Arctal works with, where no XBRL exists.
- Prompt changes (T61). A new prompt version runs beside the old one on the same golden cells. Per field, a paired test
  (McNemar on checked or not) decides; the promotion is refused if any field gets worse beyond its interval, even if the
  total improves.

## Reliability across runs (T60)

A reader that is right 80% of the time on one run is right on all five runs only about 33% of the time (0.8 to the
fifth power). T60 runs a stratified sample of tasks k times per reader at the production settings and reports both
pass@k (right at least once) and pass^k (right every time). A cell whose answer changes between runs is listed as
unstable, a finding in its own right. Sampled, not run on every company, because every run costs subscription time.

## Run logs

Every agent call writes model, input and output tokens, seconds, attempts and the task's hash into `_run`, loaded into
the `runs` table. The readers run with no tools (`--tools ""`), so the path an agent takes is one call and at most one
retry: the attempt count is the trajectory. `ledger/cost.py` turns the runs into cost per step, per company and per
release at list price (the agents run on a subscription, so this is what the work would cost, not what was paid).

## Gates

- Before a commit: `ledger golden --check`, then the suite. `ledger test` writes `reports/tests.json` (T30); the
  Release page shows a failed run in red, a run on another commit or a dirty tree as stale, a missing run in grey.
- Before a release: `release.gates`, per company. G1 failures, G4 blocks, G5 hand-check, G6 decisions a run left for a
  person to confirm. Any failing row refuses the release, and a release is signed by a person on the Release page.
- Per agent: the T49 score and the T61 paired gate give per-reader limits, so a gain in one reader cannot hide a loss
  in another.

## Watching for change

- `ledger watch` asks the SEC for 10-Ks and 10-K/As the ledger has not read; `--run` reads them.
- A person's resolution is keyed to a hash of the item's content, so it holds only while the item is unchanged; a
  changed item comes back on its own (`ledger/resolutions.py`).
- T57 adds the rest: every question has an owner role (data, expert or client), a scope and a count of the cells it
  governs; new evidence that agrees attaches quietly, and evidence that contradicts reopens the question and routes it
  to its owner.
- T55 makes the dataset answer "what did it say on date D" from filing dates, with a test that no figure filed after D
  leaks into an earlier view. Investors who backtest need this, or their history knows the future.

## Cost

The measure of the pipeline is what the next company costs: agent time and tokens (`ledger/cost.py`, built) and a
person's minutes per stage (T38). T35 times Micron through every stage, and T52 widens to 100 companies in batches, so
`reports/company-cost.md` shows the curve: whether company 50 costs less of a person than company 7.

## Closing the loop

A failure met on a real filing becomes a row in the failure log, a rule or a guard that catches it, and a fixture the
golden test holds. A judgement a person makes becomes a definition or a rule, so it applies on every run and the item
does not come back (T36 turns an explanation into a rule from Reconcile). A new model or prompt goes through T61 before
it replaces the old one.

## Not used here, on purpose

- Retrieval scoring (recall@k, MRR). There is no search step: each task holds the located tables or the passages that
  mention AI next to spending, chosen by code.
- Simulated users. The agents do not converse; each call is one task and one answer.
- Model judges and pairwise comparisons. Every check is code, so there is no judge to align and no position or length
  bias to control.
