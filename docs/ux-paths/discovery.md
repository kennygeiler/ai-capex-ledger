# App Discovery

Kenny's Data Emporium (`ledger/web/`, port 3610). Discovered 2026-11-04 from code and read-only GETs against the running
copy (`readonly: false`, release `v1.9.0` not signable: Proposed, Needs review and Golden test lines fail).

## Application Type

A single-page, hash-routed review and publishing workbench over a Python + DuckDB pipeline that turns SEC 10-K filings
into a verified capex dataset. One person reviews what code could not decide, grades a hand-check sample, and signs each
release; everyone else reads. The same server runs as a hosted read-only copy (`LEDGER_READONLY=1`).

## Tech Stack

- Server: Python stdlib `http.server.ThreadingHTTPServer` (`ledger/web/app.py`, `Handler`); DuckDB `data/ledger.duckdb`
  opened per request; JSON read API under `/api/v1/` (docs/API.md); `Cache-Control: no-store` on every response.
- Client: no framework. `app.html` shell + `pages/*.js` (one script per page, a hand-rolled `h()` element builder),
  `_router.js` on `hashchange`. Tabler 1.3.2 CSS (CDN), Inter (Google Fonts), Plotly 2.34.0 (Explore only).
- State words: `/pages/_states.js` is generated per request from `ledger/core/states.py` (`STATES`, `STATE_GROUPS`,
  `STATE_ABSENT`); pages read them only through `stateWord()` / `stateGroups()`.
- Filing viewer: `/filing/<accession>` served by `ledger/web/viewer.py` with its own CSP.
- Persistence for writes: append-only JSONL / YAML / JSON files in the repo (decisions, rules, definitions, taxonomy, gold,
  views), plus `releases/v*/` and Postgres on sign.
- Per-viewer browser storage: `localStorage` `datahq-me` (Signer name), `datahq-colors` (Explore series colours).

## User Roles

| Role | Who | What they can do | Gate |
|---|---|---|---|
| Owner / reviewer / signer | Kenny Geiler (`config.PEOPLE = ["Kenny Geiler"]`) on a local checkout | Everything: gold verdicts (Right / Wrong / Can't say), Reconcile decisions (Accept / Explain / Fix / Block release, Confirm, Overturn), mapping Approve / Reject / Choose another / Map, Make this a rule / definition, Save as view / Delete, Sign | The **Signer** box in the header (default "Kenny Geiler", saved in localStorage). Empty Signer disables Approve, Choose another, Make this a rule/definition, gold verdict buttons and Sign (tooltip "Enter a signer name"). Server refuses a `by` not on `config.PEOPLE` (400). |
| Read-only visitor | anyone on the hosted copy (`LEDGER_READONLY=1`) | Every page and GET; packet download; CSV/JSON export | Header Signer box replaced by "Read-only"; scope line ends "· Read-only". Every POST returns 403 "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository". Buttons still render; the error appears inline after a click. |
| New operator | someone taking the system over | Reads **Docs** (How it works, Operating guide, Glossary, Map, States, Rules and checks, Evaluation, Known limitations, Handoff), the Rules page and Known gaps; runs CLI commands from a checkout | none (read only); their writes would need their name added to `config.PEOPLE` |
| Unnamed local user | someone else at the local copy with a different Signer name | Can type any name; writes are refused 400 by the server | `config.PEOPLE` |

## Feature Map

### Global shell (`app.html`, `_router.js`, `_shared.js`)
- Navbar brand "Kenny's Data Emporium" (→ `#proof`); tabs Proof, Rules, Reconcile, Dataset, Explore, Release, Known gaps, Docs; active tab highlighted (`company`/`tables` → Dataset, `views` → Explore, `evidence` → Proof).
- Jump box "Ticker or company…" with a datalist of in-scope companies; on change navigates to `#data?ticker=<T>` (accepts name or any 1–6 letter ticker).
- Signer box `#me` (label "Signer"), persisted to `localStorage.datahq-me`; enables/disables write buttons live.
- Scope line under the nav: "<n> companies · Data as of <date>" (+ " · Read-only").
- "Skip to content" link; hidden h1 per route ("Kenny's Data Emporium, Proof" etc.).
- Route errors: any thrown error replaces the view with `<p class="msg bad">message</p>`. Initial "Loading…".
- Drawer (right side panel, Close button, Escape closes, focus returns to opener); used by Dataset grid company picker and Explore save.
- Crop lightbox (`cropBox`): click a crop thumbnail → full-size crop with caption, "Open in filing", "sec.gov ↗", close button; Escape or click outside closes.
- Sortable table headers (click toggles direction); expandable detail rows (Enter/Space on a row).

### Proof (`#proof`)
- Header "Proof", "<k> of 6 proven"; "Tables unchanged/Tables changed · <date>" or "Tables: not compared" (tooltip "Nothing changed since the freeze; not a correctness check"); "Hand check: <state>" link scrolls to `#gold`.
- Company table: one row per proven company (MSFT, GOOGL, AMZN, NVDA, APLD, AMD), stage columns Filings · Statement figures · Note figures · AI disclosures · Category mapping · Guidance and projects · Release, each cell "checked · done · explained · open (blocked)" with hover breakdown; last column "Proven" or "<n> to review". Row click / Enter → `#proof/<T>`. Currently all six "to review".
- Legend (Checked · Located/Done · Unverified · To review).
- "Verification source" table (Strongest first): SEC XBRL, Other company document, Ties to total, Later actual, Later filing, Citation only, Rows; plus "All".
- Failure types card (pareto charts per cause class / per check, table Type · Cause class · Origin · Check · Companies seen; "Failure types unavailable", "Chart unavailable").
- "Releases" table: Version, Signed / "Not signed" / "· not published", Values, To review at signing, Unmapped at signing, Companies, Packet "Download" (`/packet/<v>.zip`); note link "Next release" → `#release`.
- "Regression test" collapsible: Steps (Pass / Fail (exit)), Differences (Table, Added, Missing).
- **Hand check** (gold set, `#gold`): "20 items per company · random sample · Unchecked never passes"; per-group error lines ("x right · y wrong · z can't say · n unchecked · error rate a% (95% CI …)"); company picker buttons "<T> done/20". Picking a company shows a table Item · Value · Source · Check, grouped (No SEC counterpart, Definition differs, Not extracted, Not reconciled, Calculated, Matches SEC XBRL), hard items first. Per item: crop thumbnail(s) + "Open"/"sec.gov ↗", value as filed ("In millions · $…"), live drift ("Now $…", "Removed from dataset", "Current value unavailable"); verdict buttons **Right / Wrong / Can't say**, note input "Note (required for Wrong / Can't say)", status "<word> · <by> · <date>" or "Unchecked". Errors: "Note required", server message inline; "Hand check unavailable", "No hand-check sample yet", "Hand-check files with errors: …", "Groups as drawn · live tables unavailable". Live: 119 of 120 checked (APLD 1 unchecked).

### Company trail (`#proof/<T>`)
- Header: company name + ticker, colour legend (Verified, Corroborated, Matches company tag, Done, Unverified, Proposed, Needs review, Blocks release), "Not in scope" for non-proven; "Proven" or "<n> to review"; links "Reconcile" (`#reconcile?scope=T`) and "Dataset" (`#data?ticker=T`).
- Summary card "Before release" / "Ready for release", "As of …", "Review in Reconcile →"; tiles Coverage ("Through 10-K · FY ending …", "Filed …", "Next 10-K expected ~…", "<n> new filings not read", SEC check freshness: "SEC checked <h>h ago" / "out of date" / "SEC never checked" / "SEC check failed"), Verification (Figures, Match SEC XBRL, Tie to totals, Confirmed in 2 filings, Citation only, To review, Quotes verified), Last release ("Signed … · …" or "None"), Changes since release (added/changed/removed + "Details").
- One card per stage with "<n> items · <k> to review" or "Complete"; table Item · Value · Source · Verification; open items first, the rest collapsed under a tally summary ("12 verified · 3 corroborated …").
- Source: calc block (formula, arithmetic, cross-checks "matches"/"includes"/"differs by"/"No total to compare", "Stored value $…"), crop thumbnails (lightbox), "Open" (in-app viewer, "Open in filing, the cell outlined"), "sec.gov ↗", crop states "Cell located / Cell not located / Crop out of date / Crop file missing / No crop".
- Verification: row word + short reason; expandable detail (`details.why`); "Restated" line + "Compare filings" link.
- Category mapping stage renders mapping decision cards (Company line, Proposed, Source, Company's own tag, Basis, Alternatives, Affects) with "Decide in Reconcile →" / "Confirm or override in Reconcile →".

### Evidence (`#evidence/<id>`, `#evidence/compare?a=&b=`)
- Single: title "<field> · <dimension> <T>", period; "Company trail" link; two columns **Extracted** (value, Cited cell, Row, Column, Units, Period, Filing, Source) and **Filing** (crop state, crop image linking to viewer, "Page shows … · cropped …", "<n> rows folded", "Open in filing" button, "sec.gov ↗").
- Compare: "Filing A · 10-K filed …" vs "Filing B …", "Readings differ" / "Readings agree", wide two-crop layout.
- Errors: unknown id → 404 "no cited cell '<id>'" shown as page error; missing a/b → "Two readings are needed: #evidence/compare?a=<id>&b=<id>".

### Filing viewer (`/filing/<accession>`)
- Opens in a new tab; the stored 10-K HTML with the cited cell outlined; strict CSP.
- Refusals as JSON: 404 "not a filing" / "no stored filing with that accession", 409 "the stored copy of this filing differs from its fingerprint", 410 "the stored copy of this filing is missing".
- Crops `/evidence/crops/<f>.png` served only while the crop state is located (else 404 JSON).

### Rules (`#rules`)
- "Agents · <n>" cards: name, job, Model, Prompt version; Charter (first paragraph + "Full charter" disclosure, or "No charter"); Score datagrid (Outputs · stage, SEC XBRL match "x of y · p% (95% CI …)" or "No SEC XBRL counterpart", Planted errors "Caught x of y · Missed z" or "Not measured"); "Planted errors by kind" collapsible; "Runs per company" (Documents, Calls, Input/Output tokens, Time (s), Attempts, Failed, All footer); "Prompt and model history" (When, By, Change, Versions).
- "Rules" table: Kind (Rule/Guard/Definition/Mapping), Rule, Description, Severity, Hits, Failure type.
- "To review · <n>" grouped by need: Company, Stage, Item, Detail; or "No items to review".
- No write controls (the server's `/api/agents/<id>/prompt|use|model` POST routes have no UI).

### Reconcile (`#reconcile?scope=&group=&cause=&layer=&field=&kind=&resolved=`)
- Header "Reconcile", counts Needs review / Blocks release / Proposed / Unverified, "Last run …", "Last release …", "Keyboard" hint (tooltip "j k move · Enter opens · a e f b decide · space selects").
- Filters (all write to the URL): Scope (All companies / industry / ticker), Group by (Grouped by cause / Grouped by company), Cause (Every cause …), Industry, Field, Check (Restated, Large year-over-year change, Line renamed, Capex high vs revenue, Opex above revenue), switch "Show <n> settled".
- Cards per cause (order: to_confirm, blocked, fact_differs, fact_changed, value_missing, finding_unconfirmed, new_filing, asset_types; live labels "Differs from SEC XBRL", "Rule findings", "Category mapping") or per company; header counts "<n> to review of <m>" / "<n> proposed" / mapping tallies; "Select all <n>".
- Row columns: Select checkbox, Company/Cause, Item, Dataset, SEC XBRL (≥/≤), Gap bar, Difference (+/−, %), Decision.
- Row click / Enter / o expands evidence: aligned diff tables (This year, Computation, By year, Release vs Now, Before/After), "Company trail", "Open in Dataset", "Open in EDGAR ↗", "Note wording" ("Note text unavailable"), "Proposed: …", "Rejected: …".
- Decision form: btn-group **Accept / Explain / Fix / Block release** (tooltips "Right as it stands", "Right, with the reason kept", "Wrong; stays open until re-read", "Blocks release until settled"), Reason input, **Save** ("Reason required", "Saving…", "Saved.", "Couldn't save: …. Try again.").
- After an Accept/Explain save on an encodable item: "Saved. Apply to every company?" + encode panel + "Done".
- "Apply everywhere" card: **Make this a rule** / **Make this a definition** with "Applies to: …", reason input; "Writing…", "Saved to <file>. Applies on the next run.", "Couldn't write: …".
- Proposed (to_confirm) rows: **Confirm <Accept|Explain|…>** and **Overturn**; "Confirmed." then reload.
- Category mapping rows: **Approve** / **Reject** / **Choose another** (or **Map** when no proposal); decision card with "Standard category" select; "Mapped.", "Confirmed.", "Rejected.", 409 "Changed since loaded. Reloading."; mappings never bulk-selected.
- Bulk: selecting rows shows "<n> selected: …" card with the same decision form ("Why, for all <n>…", **Save for <n>**) and **Clear**.
- Keyboard: j/↓, k/↑ move; Enter/o expand; Escape collapse; space select; a/e/f/b open and pick Accept/Explain/Fix/Block release.
- Empty: "No items to review". Live: 69 rows (wait 29, bad 16, company 18, info 6).

### Dataset (`#data?list=&ticker=&has_value=`, `#data?view=grid&t=&f=&k=&y=`, `#company/<T>`, `#tables/<list>`)
- View switch **Rows / Grid**.
- Rows: list sidebar All rows (All measures), Values, Facts, Statements, Projects, Companies; Company select ("Every company"), taxonomy-only "Every row / With a value / Without a value", "Find in rows" search (150 ms debounce), "<n> rows of <m>"; **CSV** and **JSON** links; sortable columns, row expands to a key/value detail; ticker cells link to the trail; "No rows.".
- Grid: Field select, Companies group (All companies, Buyers, Sellers, industries, "Custom…" opens a drawer with checkboxes + **Apply**), Kind (Every measure / Spent / Committed / Derived / Planned); company × year cells with marks (✓ Verified · ○ Unverified · ≠ Differs from SEC XBRL), cell click opens provenance (sources, crop, "Open in 10-K ↗", decision); badges Fix pending / Accepted / Explained / Blocks release / "Not checked"; **Export CSV** (client-side blob).

### Explore (`#explore`, `#explore/<viewId>`, `#explore?<state>`, `#views/<id>`)
- Left: "<n> saved views" (live 4) + "New".
- Controls: Measure (All measures, Statement figures, Note figures, Quoted statements, Named projects), taxonomy Measure/Category/Standard type, Field, Kind, Value ("the value as reported" / "change from the prior year"), Layer, Tickers (comma-separated), From/To, X axis, Series, Chart type (bars, stacked bars, lines, share of total).
- Plotly chart (hover, drag-zoom, double-click reset, legend toggles; >8 series folded into "Other"); "Data" disclosure table; click a bar → its rows; "Show rows".
- **Save as view** / **Save changes** (drawer: Name, Note, **Save**); **Delete** → "Confirm delete" (arms for a few seconds).
- JSON / CSV links. Empty "No rows match"; "Chart unavailable" when Plotly missing.
- Defect found: Save and Delete POST without `Content-Type: application/json`, so the server refuses them (403 "a write needs Content-Type: application/json"); Delete has no error handling.

### Release (`#release?version=`)
- Header "Release", "v1.9.0 · Compared with v1.8.0 · <n> companies · <k of m> required checks pass".
- **Sign <version>** button: disabled unless every required line passes and Signer is set; status text "<n> required checks failing" / "Enter a signer name" / "Signs and publishes <v>"; browser `confirm("Sign and publish <v> as <me>?")`; "Signing <v>…"; success "<v> signed by … · <hash>" + "Published: …" then redirect to Proof after 2.5 s, or "Signed, not published: <error>" (stays).
- Checklist table: State (Pass / Fail / Info / Not run / Stale), Check, Count, Required/Optional, Details, "Fix in" link (Proof, Reconcile, Dataset, Known gaps, Release, Rules); row expands detail table ("No items").
- "Release checks by company" (gates G1/G4/G5/G6 per ticker, Pass/Fail); "Packet <v>" (File, Rows, Bytes, "Fingerprint <hash8>"); "Changes since <prev>" (List, Rows, Added, Removed, Changed, Columns) or "First release".
- Live: not signable (Proposed, Needs review, Golden test fail).

### Known gaps (`#gaps`)
- Header "Known gaps", counts Holds / Partial / Not built / Out of date / Planned, "<n> open issues", "Updated …", warnings "Issue log append-only: not enforced here" / "Issue log edited".
- "Unregistered claims · <n>" alert; "Claims · <n>" table (Claim, Where = page names, Status + "Declared …", Gaps); "Open issues · <n>" (Severity, Issue, Claim, "Logged <date> · <id>"). Read only.

### Docs (`#docs/<slug>`)
- Sidebar "Docs pages": How it works, Operating guide, Glossary, Map, States, Rules and checks, Evaluation, Known limitations, Handoff; unknown slug falls back to the first.
- Markdown render (tables, code, links resolved to `#docs/…` or `/docs/<file>`), the overview's mermaid flowchart drawn as clickable boxes (Filings → #proof, Read → #rules, Check → #proof, Review → #reconcile, Release → #release, Database → #data).
- Footer "Source: docs/<file>.md" (plain-text link) or "Written from code on every request" (Glossary, Rules and checks).

## Navigation Structure

```
Navbar: Proof | Rules | Reconcile | Dataset | Explore | Release | Known gaps | Docs   [Ticker or company…] [Signer]
#proof ──row──> #proof/<T> ──> #reconcile?scope=T, #data?ticker=T, #evidence/compare?a&b, /filing/<acc> (new tab), sec.gov
   ├─ Hand check (in-page #gold) ─ company picker ─ verdicts
   ├─ Releases ─ /packet/<v>.zip, Next release → #release
#reconcile ──expand──> evidence ─ Company trail (#proof/T), Open in Dataset, Open in EDGAR ↗
#release ── "Fix in" → Proof / Reconcile / Dataset / Known gaps / Rules ── Sign → (success) #proof
#data (Rows|Grid) ── ticker cell → #proof/T ;  #company/T → Dataset ;  #tables/<list> → redirect to #data?list=
#explore ── saved views #explore/<id> ;  click bar → rows → #proof/T
#docs/<slug> ── flow diagram boxes → app routes
Default / unknown route → Proof.
```
All filters live in the hash query, so every filtered state is linkable and Back/Forward works.

## Data Entities

| Entity | Store | C | R | U | D | UI surface |
|---|---|---|---|---|---|---|
| Company | `config.py` (PROVEN/SCOPE, INDUSTRIES), `companies` list | CLI | all pages | CLI | – | Jump box, Proof, trail |
| Filing / document | `documents`, `data/raw` | CLI ingest | trail, viewer | – | – | `/filing/<acc>` |
| Value / fact / statement / project / taxonomy row | DuckDB | CLI extract | Dataset, Explore, trail, API | via decisions/rules | – | Dataset, Explore |
| Cited cell + crop | `reports/evidence/crops.json`, PNGs | CLI `evidence --crops` | trail, gold, evidence | – | – | lightbox, Evidence |
| Resolution (decision) | `decisions/resolutions.jsonl` (append) | Reconcile Save / bulk / Confirm | Reconcile, trail, Dataset | new line supersedes (Overturn, Change decision) | – | Reconcile |
| Rule / definition | `rules/*.yaml`, `definitions/companies.yaml` | Make this a rule / definition | Rules | file edit | – | Reconcile, Rules |
| Category mapping | `taxonomy/asset_types.yaml` (+ rejected log) | Approve / Map / Choose another | Reconcile, trail | Approve (confirm), 409 on stale `expected` | Reject logs rejection | Reconcile |
| Gold item / verdict | `gold/<T>.json` | sample via CLI | Hand check | Right / Wrong / Can't say (re-vote allowed, any→any) | – | Proof |
| Saved view | `data/views.json` | Save as view | Explore | Save changes | Delete (Confirm delete) | Explore |
| Release | `releases/v*/`, SIGNOFF.json, Postgres | Sign | Proof Releases, Release | – | – | Release |
| Agent / prompt / model | `agents/agents.json`, `agents/prompts/` | API only | Rules | API only | – | Rules |
| Claim / finding | `claims/claims.yaml`, `claims/findings.jsonl` | CLI | Known gaps | CLI append | – | Known gaps |

State machines (`ledger/core/states.py`, `/api/v1/states`):
- **row** (M1): ok Verified, corroborated Corroborated, company Matches company tag, done Done, info Unverified, wait Proposed, bad Needs review, blocked Blocks release, unknown Not checked. Decision moves: accept/explain → explained (info), fix → open (bad), blocks → blocked; wait → done/bad/info on Confirm/Overturn.
- **ladder** (M1b): xbrl, filer_tag, tie, reading, keyed, citation_only, explained, readings_differ, differs, not_looked_up.
- **check** (M1a, Dataset words): agree, unresolved "Differs from SEC XBRL", definition_gap "Unverified · definition", no_reference "Unverified · citation only", not_reported "Not reported", not_extracted "In SEC XBRL, not extracted", unknown.
- **mapping** (M5): unmapped "Unmapped" → to_confirm → confirmed / filer_tag; filer_tag → confirmed.
- **crop** (M14): located, not_located, stale, missing, none.
- **gold** (M7): unchecked → right/wrong/cant_say, freely between the three; never back to unchecked.
- **gold_group** (M17), **crosscheck** (M18), **line** (M9: pass/fail/info/not_run/stale), **edgar** (M12: fresh/stale/never/unreadable, 48 h).

Write guards (every POST): read-only 403 → Content-Type must be application/json (403) → Origin must be own (403) → body JSON object (400) → `by` on PEOPLE (400) → Stale 409 (page reloads) → Busy 503.

## Integrations

- SEC EDGAR / XBRL (ingest, CLI only; `LEDGER_OFFLINE` disables); outbound "sec.gov ↗" / "Open in 10-K ↗" / "Open in EDGAR ↗" links (only `https://www.sec.gov/` hrefs become links).
- Headless `claude -p` agents (extraction, CLI only); costs and runs shown on Rules.
- Postgres publish on Sign (failure surfaces "Signed, not published: …").
- CDNs: Tabler CSS (jsdelivr), Plotly (cdnjs), Google Fonts.
- Read API `/api/v1/<list>[.csv]` with filters and `as_of`; packet zip `/packet/<v>.zip`; docs plain text `/docs/<NAME>.md`.

## Recommended Story Topics

1. proof-hand-check | Proof overview and hand-check grading | The owner's core trust loop: read the proven board, pick a company, grade gold items Right / Wrong / Can't say with notes and crops.
2. company-trail-evidence | Company trail and evidence drill-down | Every figure's provenance: stage cards, crop lightbox, Open in filing viewer, Compare filings, and viewer refusals.
3. reconcile-decisions | Reconcile: deciding open items | The main write workflow: filters, expand evidence, Accept / Explain / Fix / Block release, Confirm / Overturn, bulk Save for n, keyboard j/k/a/e/f/b.
4. reconcile-mapping-encode | Category mapping and apply-everywhere | Approve / Reject / Choose another / Map with 409 stale handling, and Make this a rule / definition after a save.
5. release-sign | Release checklist and signing | The gate: failing lines with Fix in links, Signer requirement, Sign confirm, published vs signed-not-published, packet download.
6. dataset-explore | Dataset rows/grid and Explore charts | Consumers' read path: lists, search, CSV/JSON, grid picker drawer, Plotly charts, saved views (including the broken Save/Delete content-type).
7. readonly-visitor | Hosted read-only visitor | LEDGER_READONLY: Read-only label, every write button refused 403 inline, reads and exports still work.
8. operator-onboarding | New operator: Docs, Rules, Known gaps | Takeover path: Docs sidebar and flow diagram, agents/rules/scores on Rules, claims and open issues on Known gaps, empty/error states.
