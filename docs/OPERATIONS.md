# Operating guide

The routine work of running the ledger: the daily review, grading the gold set, adding a company, cutting a release, and
what to do when a Release line is red. Setup and the objects are in [Handoff](HANDOFF.md); what each word means is in the
[Glossary](#docs/glossary). Commands are `uv run python -m ledger <command>`, shortened here to `ledger <command>`.

## Never

1. **Never sign a release that was not reviewed.** Signing is the one human act and belongs to the owner. Agents never sign or publish.
2. **Never run the agents on the paid API.** They run headless on a Claude subscription through `claude -p` (`LEDGER_CLAUDE`).
3. **Never edit a prompt or the taxonomy in place.** A prompt change is the next version in `agents/prompts/` (`<agent>@v<n>`), switched on in `agents/agents.json` as a second step. A taxonomy or mapping change goes through Reconcile or a reviewed commit.
4. **Never ingest in a worktree.** Worktrees share `data/raw`, `data/docs` and `data/text` with the main checkout; an ingest on an older base rewrites the shared parses with old code. Run `ingest` only on current main.
5. **Never freeze golden by accident.** `ledger golden --freeze` only on purpose, in its own commit that says why.
6. **Never edit a file under `releases/`**, `decisions/` or the agents' history. They are append-only or hashed.
7. **Never commit `.env`.** The SEC contact and the database URLs live only there.
8. **Never get around a bot check.** Investor-page links are listed by a person in `sources/ir.yaml`.

## Daily review

1. `ledger watch` asks EDGAR for 10-Ks and 10-K/As the ledger has not read; `ledger watch --run` reads them. The company trail shows the age of the last check ("SEC checked", or "out of date" after 48 hours).
2. Open [Proof](#proof). Each company in scope shows its rows by state per stage. A company is proven when nothing is open.
3. Open [Reconcile](#reconcile). Every item is open or blocked, with the evidence and the reason code could not decide it. For each:
   - **Accept** or **Explain** when the figure is right and the reason is specific to this item.
   - **Make this a rule** or **Make this a definition** when the same reason will recur: the explanation is written once (`rules/` or `definitions/companies.yaml`) and applies on every run.
   - **Fix** when the figure is wrong: the item stays open until the pipeline produces the right one.
   - **Block release** when the figure must not ship.
   - For an asset-type proposal: **Approve**, **Edit** or **Reject**. Only an approval writes `confirmed_by`.
4. After a definition or rule, run `ledger rules` (or `ledger reconcile`), then commit the changed file. The commit message says what was decided and why.
5. A new kind of failure gets a row in `docs/INGESTION.md` and `taxonomy/failures.yaml`, a check that catches it, and a test.

The name in the signer box is the author of every decision. The box is empty until a name is typed (remembered in this browser); every write refuses a name off `config.PEOPLE`. There is no sign-in yet, so the name is a claim, not proof of a person.

## Grading the gold set

The gold set (`gold/<TICKER>.json`, the Hand check on Proof) is about 10 values and 10 facts per proven company, stratified by field and year, untagged facts oversampled.

1. On [Proof](#proof), the Hand check section lists the gold items per company. Each item shows the claim, the cited cells and their crops.
2. Open the filing at the cell and give a verdict: **Right** (the filing shows this number here), **Wrong** (it shows something else) or **Can't say** (the filing does not settle it), with a note.
3. `ledger gold --status` prints the verdicts and the error rate: wrong of (right + wrong), with n and a Wilson 95% interval. Can't say is counted beside it.
4. `ledger golden --check` compares every verdict with the current tables. A Right item whose value changed fails as "changed since verdict, re-verify".
5. Each new release version draws a new sample: `ledger gold --draw`. Items with a verdict are never overwritten or dropped.

## Adding a company

1. `ledger run --ticker X` runs every step for it, agents included (network and `LEDGER_CLAUDE` required). It joins stage 3, not the release scope.
2. Give it an industry in `ledger/core/config.py` `INDUSTRIES` and a line in `docs/COMPANIES.md`.
3. Map its PP&E categories: `ledger mapper X`, then approve on `#reconcile?scope=X`.
4. Review its open items on Reconcile. It enters the proven set (`config.PROVEN`) only when nothing is open, and then the golden fixtures are frozen again on purpose.

## Cutting a release

After any merge, in this order, committing after each:

1. `ledger golden --check` (rewrites `reports/golden.json`).
2. `ledger claims` (regenerates `docs/CLAIMS.md`).
3. `ledger test` on that commit (rewrites `reports/tests.json`).

Each run records the commit, the tree and a code hash (every tracked file less the two reports and `docs/CLAIMS.md`). Both lines read the checkout at every checklist: uncommitted code, a run on a dirty tree, or a hash that differs from the checkout's reads stale and blocks the signature; committing only the three record files keeps the hash (F20). Sign and `ledger signoff` pass one gate first (`checklist.preflight`): no uncommitted code, and both run lines pass.

Then open [Release](#release). The checklist builds the packet in memory and shows every line that could make a signature wrong. When every required line is green, the Sign button writes `releases/<version>/`, signs as the name in the signer box, stores the checklist in `SIGNOFF.json` and publishes. From the command line: `ledger release vX.Y.Z` builds and prints the gate table, `ledger signoff vX.Y.Z --by "<name>"` signs, `ledger publish vX.Y.Z` pushes a signed release to Postgres.

## When a Release line is red

The page leads with the failing required lines; the passing and informational ones sit under one "N checks pass" row.
Each line's Details is one short line in product words; the files each line reads are here.

| Line | Meaning | Reads | What to do |
|---|---|---|---|
| All filings read (G1) | A filing ended in a failure that is still open | `exceptions` (the loaders' failures) | On Proof, find the failed step; rerun it (`--run`, then `--load`) or log the failure type |
| Every block has a decision (G4) | A block-severity rule fired with no current decision by a person (a run's or an agent's decision is Proposed, F14) | `exceptions`, `decisions/decisions.jsonl` | Decide each item on Reconcile, or `ledger review decide <id> … --by "<name on config.PEOPLE>" --as person` |
| Values confirmed on filing (G5) | A value XBRL cannot vouch for was not confirmed on the rendered filing | `reports/evidence/`, `golden/stage<N>-handcheck.json` | `ledger evidence --ticker X`; where the re-read cannot confirm, a person confirms in the hand-check file |
| Proposed (G6) | A run's decision (a resolution, or a decision on a block finding) or a category mapping has no person's confirmation; per company, the Proposed count every page shows | `decisions/resolutions.jsonl` ("to confirm"), `decisions/decisions.jsonl` (a block decided by a run: `author_kind` run, or a `reviewer` off config.PEOPLE or "to confirm"), `taxonomy/asset_types.yaml` (no `confirmed_by`) | Reconcile, Category mapping (Proposed) and "To confirm" |
| Needs review | Rows neither checked nor explained, nothing proposed (an unmapped category is one); per company, the Needs review count every page shows | the Proof board (`proof.board`), `taxonomy/asset_types.yaml` | Reconcile; an unmapped category: `ledger mapper X`, then approve |
| Blocks release | A block rule or a decision refuses the release; per company, the Blocks release count every page shows | the Proof board | Reconcile |
| Answer-key values missing from the dataset | XBRL holds a value the dataset does not ship and nothing accounts for it | `reference_values`, `values`, `decisions/` | Rerun the reader for the filing, or resolve the row on Reconcile |
| Verified or explained with no record behind it | A verified or explained row in scope names no record, or one not on file (F16; the walk `proof.unevidenced` on the live tables) | the Proof board, `decisions/resolutions.jsonl`, `definitions/companies.yaml`, `rules/`, `taxonomy/asset_types.yaml`, `texts` | Open the trail the detail links; restore the record or reopen the row |
| Hand check | An item has no verdict, or a verdict no longer holds | `gold/*.json`, live | Give or re-check the verdict on Proof |
| Regression test | Tables differ from the frozen expectation, or the check ran on another commit or a dirty tree (stale, F20; a report with no commit is stale) | `reports/golden.json` (`git`, `dirty`) | Fix the code, or freeze on purpose with the reason; `ledger golden --check` on the commit being signed |
| Test run | Failed, not run, or run on another commit or a dirty tree | `reports/tests.json` | `ledger test` on the commit being signed. Required since a00b67f; releases up to v1.8.0 were signed while the line only informed, and their `SIGNOFF.json` records it as not run with `required: false` |
| Claims register | A shown string has no row in `claims/claims.yaml`, or a finding was edited | `claims/claims.yaml`, `claims/findings.jsonl` | Register the string; restore the finding log |
| Claims doc current | `docs/CLAIMS.md` differs from the register (a test run no longer changes it: the run, the golden report and the gold count are read live) | `docs/CLAIMS.md` | `ledger claims`, then commit |
| Previous releases readable | A signed release no longer matches its hash | `releases/v*/manifest.json` | Investigate; never edit `releases/` |
| Packet | The version's folder exists with other content | `releases/<version>/` | Use the next version |

Info lines (rows with no value from `taxonomy.csv`, rows changed against the previous `releases/v*/`, known gaps, limitations with no mitigation from `taxonomy/limitations.yaml`) never block. They are read before signing.

## Keeping the docs true

`docs/CLAIMS.md` is generated; never edit it by hand. The glossary and the rules page are written from code. A change to a
state word is made in `ledger/core/states.py` only. Every string a page shows as a claim needs a row in `claims/claims.yaml`.
