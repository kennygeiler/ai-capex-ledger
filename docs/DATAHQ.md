# DATAHQ: the proof, shown

The design before 31 Oct 2026, with its audits and the three Reconcile passes, is in `docs/archive/DATAHQ-before-proof.md`.
What follows is the app as it is now, built around `docs/PROOF.md`: a pipeline that proves every number it produces,
on five companies first.

## Pages

- **Proof** (home, `#proof`): the proven set down, the stages across (ingest, values, facts, statements, attribution,
  plans and projects, release). Each cell: checked · explained · open. A company reads "proven" when nothing is open at
  any stage. One line for the other 95 companies, with their counts and the note that they are not yet proven. The
  golden test's last result sits in the corner.
- **Company trail** (`#proof/TICKER`): one card per stage: how many items, how many checked, explained, open; the open
  items with what they need (a definition, a rule, a method fix); the explained items with what explains them (a
  definition by name, a guard by name, a decision, "no tagged counterpart", "restated between filings").
- **Rules** (`#rules`): every rule in the registry, every code guard (part-year amount, program words, restatement
  between filings, comparability by scope, accrual against cash) and every definition on file for the proven set, with
  what each fired or closed in the latest run and the failure type it came from. Below, the open items of the proven
  set grouped by what is missing. That list is the work.
- **Golden** (`#golden`): whether the code stages reproduce the expected tables from the frozen inputs, when it last
  ran, each step's exit, any differences, and the commands.
- Kept: **Reconcile** (judgement on open items, keyboard, bulk, the gap bar and the diff tables), **Dataset** (the
  grid with marks: ✓ traced, ≠ differs from SEC data, ✗ disagrees with a stated figure, ! above the total, a person's
  decision as a badge), **Attribution** (the heat grid by layer with method badges, the theses), **Explore** (Plotly,
  share as a value, saved views as API queries), **Releases**, **Agents**. Flow and Status still answer their hashes
  but are off the navbar; their counts live on Proof.

## How it is built

Tabler (`@tabler/core@1.3.2`, jsDelivr, pinned) for the whole page; a bridge stylesheet maps the app's own layout
classes onto the kit's tokens; a post-render pass puts the kit's classes on every hand-built control. One HTML file,
`ledger/app.html`, served by `ledger app`; every page reads `/api/v1/...` (`docs/API.md`). `ledger/proof.py` is the
model behind Proof, the trail and Rules; `ledger/golden.py` behind Golden.

## What a person does here

Reads Proof. Opens a company that is not proven. Each open item says what is missing: a definition (write it in
`definitions/companies.yaml`), a rule (a check in `rules/` or a guard in code, with its failure type in
`docs/INGESTION.md`), a method fix (the thesis, versioned, dry-run, switched). Reruns the step. The item is explained
or checked, and never comes back. Reconcile is for the rare true judgement, and a judgement that would be made twice
becomes a definition.
