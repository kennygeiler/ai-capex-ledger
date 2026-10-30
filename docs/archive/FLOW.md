# The flow screen: spec

What the product is (Kenny, 29 Oct): a pipeline ingests filings and cleans the numbers with no one in the loop; an
agent with an industry-specific view of how money flows reads the cleaned data and picks out the AI spend; a person
tunes that view, reruns, and watches the dataset change; insights sit on top. The user is an Arctal data scientist,
whose job is to own a dataset other people pay for: see what came in, see what the pipeline made of it, see what broke
or disagrees, fix the definition or the method, rerun, check against references, release, and tell the consumer what
moved.

## Independent review (29 Oct) and what changed in the spec

An independent product review of the first spec: the screen followed the pipeline (extract, method, attribute, insight),
not the job (open issues, their downstream impact, resolution, release). Release, the step that makes the dataset
sellable, was outside the flow. Nothing recorded whether an item was accepted, explained, fixed or blocking. Passing
counts (1,431 of 1,431) are noise at scale; only exceptions matter. The taxonomy (spent, committed, planned) was absent.
Verdict: build with the changes. Taken: home is a queue of issues; the flow ends at Release with what blocks it, the
diff against the last signed release and a drafted change note; Extracted shows gaps and disagreements only; the
reference check sits with Attribution; Insight is cut from the flow (it is the consumer's view). Not taken yet: a dry
run of a method edit before switching it on (needs a run-with-version option in the attributor), and persisted item
states beyond what the data derives (blocked, disagrees, moved, new).

## Second review, on the built screen (29 Oct), and what changed

Ten seconds at 9am: no. The queue was sorted by state then alphabetically, so nine identical "fact differs" rows came
first; "Touches" said "a fact the attributor may use" on every row; Release said "Nothing blocks" above 39 open items;
the drawer gave no cell, no tag value, no affected attribution. Verdict: ship with the changes, one non-negotiable:
the release gate must read what a person has resolved. Taken: the queue is ranked by dollars at stake (the
attributions a fact feeds, the gap between ours and a stated reference, the amount that moved), with a "new since the
last signed release" flag; facts that feed no attribution are collapsed into one line; resolutions (accept, explain,
fix, blocks) are an append-only log in `resolutions.jsonl`, keyed by the item and a hash of its content, and
Release reads them: a blocking resolution blocks, accept and explain hide the item until its content changes, and the
line says "gates pass, but N unresolved" rather than "nothing blocks"; the drawer shows ours, the tag, the delta, the
cell and its filing, the attributions the fact feeds, the value in the last release, and the resolution controls.
Then the dry run: a saved model version that is not in use can be run against its industry from the model drawer (`attribution --model-version X@vN --dry-run`); the result is which rows would change, before and after, and how the reference check would move; the table is untouched until a person clicks Use. A definition dry run is still open.

## The screen

Home. A queue on the left: every issue for the scope, one row each, with where it is, what it touches downstream, and
the action that resolves it. Four stages across the top as context: Extracted (gaps and disagreements only), Method
(model in use, edit, rerun), Attribution (amounts by method and by spent / committed / planned, what moved, the
reference check), Release (what blocks it, the diff against the last signed release, a drafted change note). Clicking
a queue row opens the item with its trail: the filing, the fact, the attribution, the reference. The original five-stage
sketch is kept below for the record.

```
 What changed            Extracted                Method                  Attribution             Insight
 since last run/release  values  354/384 ✓XBRL    hyperscaler@v2 (5 cos)  AI capex: 40 amounts    buyers' AI capex vs
 2 new filings           facts   525/1448 tagged  uses: PP&E categories,  by method: 24 PPE…      total capex, by year
 14 facts changed        statements 83            stated shares, leases   changed since last      reference: 2 agree,
 2 attributions moved    cells re-read 1431/1431  traps: leases, JVs      load: 2 → open           3 disagree
 1 reference disagrees   [open any list]          [edit] [rerun industry] [open grid]             [open insights]
```

- **What changed**: new filings and texts since the last run; values, facts and attribution rows that moved since the
  last release; references that disagree. Each line opens the list. Empty when nothing happened, and says so.
- **Extracted**: counts with their checks for the scope (values agreeing with XBRL, facts agreeing with tags, statements
  quoted, cells re-read). Each opens the list of items, and each item opens its provenance.
- **Method**: the model in use for the scope's industry (or the list when the scope spans several), what it draws on,
  its traps, the prompt version. Edit saves the next version; Use switches it on; Rerun runs the attributor for the
  industry. The change log is one click away.
- **Attribution**: the numbers the method produced for the scope: how many carry an amount, by method; what moved in
  the last load, with before and after; the grid behind it.
- **Insight**: the two charts that matter (AI capex inside total capex by year; reference check), and the link to the
  full set.

Scope is a select in the bar; the URL carries it. The Dataset tab is the consumer's grid with export; Status, Releases
and Agents stay as they are.

## Why this and not the grid

The grid is the deliverable. The flow is the work. A data scientist opens the console because something happened, and
needs to see in one glance what it touched downstream and what to do about it. The grid cannot show that; the flow
cannot replace the grid for the consumer. Two views, one data.
