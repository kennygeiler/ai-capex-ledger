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

The name in the signer box is the author of every decision. It must be on `config.PEOPLE`; there is no sign-in yet, so the name is a claim, not proof of a person.

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

Then open [Release](#release). The checklist builds the packet in memory and shows every line that could make a signature wrong. When every required line is green, the Sign button writes `releases/<version>/`, signs as the name in the signer box, stores the checklist in `SIGNOFF.json` and publishes. From the command line: `ledger release vX.Y.Z` builds and prints the gate table, `ledger signoff vX.Y.Z --by "<name>"` signs, `ledger publish vX.Y.Z` pushes a signed release to Postgres.

## When a Release line is red

| Line | Meaning | What to do |
|---|---|---|
| All filings read (G1) | A filing ended in a failure that is still open | On Proof, find the failed step; rerun it (`--run`, then `--load`) or log the failure type |
| Every block has a decision (G4) | A block-severity rule fired with no current decision | Decide each item on Reconcile |
| Values confirmed on filing (G5) | A value XBRL cannot vouch for was not confirmed on the rendered filing | `ledger evidence --ticker X`; where the re-read cannot confirm, a person confirms in the hand-check file |
| No proposal left to confirm (G6) | A run's decision or an asset-type mapping has no person's confirmation | Reconcile, "to confirm" and "asset types" groups |
| Items to review | Rows neither checked nor explained | Reconcile |
| Items blocking release | A block rule or a decision refuses the release | Reconcile |
| Answer-key values missing from the dataset | XBRL holds a value the dataset does not ship and nothing accounts for it | Rerun the reader for the filing, or resolve the row on Reconcile |
| Decisions left to confirm | A run decided; a person has not confirmed | Reconcile, `?cause=to_confirm` |
| Unmapped asset types | A reported PP&E category has no entry | `ledger mapper X`, then approve |
| Golden test | Tables differ from the frozen expectation, or gold fails or is unverified | Fix the code, or freeze on purpose with the reason; give or re-check gold verdicts |
| Test run | Failed, or run on another commit or a dirty tree | `ledger test` on the commit being signed |
| Claims register | A shown string has no row in `claims/claims.yaml`, or a finding was edited | Register the string; restore the finding log |
| Claims doc current | `docs/CLAIMS.md` differs from the register | `ledger claims`, then commit |
| Previous releases readable | A signed release no longer matches its hash | Investigate; never edit `releases/` |
| Packet | The version's folder exists with other content | Use the next version |

Info lines (rows with no value, rows changed, known gaps, limitations with no mitigation) never block. They are read before signing.

## Keeping the docs true

`docs/CLAIMS.md` is generated; never edit it by hand. The glossary and the rules page are written from code. A change to a
state word is made in `ledger/core/states.py` only. Every string a page shows as a claim needs a row in `claims/claims.yaml`.
