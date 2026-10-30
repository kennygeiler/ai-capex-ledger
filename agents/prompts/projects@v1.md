# Projects prompt: projects@v1

You are reading passages from one company text (a 10-K MD&A, an earnings release or a call transcript). Your job: list every named project the company is building, buying or contracting for the AI buildout, with its size and stage, each as a verbatim quote.

## What a project is

A thing with a name or a place and a size, that the company is spending on or has committed to: a data-center campus or site, a fab, a plant expansion, a power plant or nuclear restart, a power purchase agreement, a GPU cluster or supercomputer, a multi-year cloud or GPU commitment, a network build. Not a project: a product launch, a hire, a general statement of intent ("we will continue to invest"), a figure for total capex, revenue, or a customer's project the company only supplies.

## Fields

| Field | Give |
|---|---|
| `name` | The project as the company names it ("Crane Clean Energy Center", "Ellendale HPC campus", "Stargate"), or the place and kind when it has no name ("Abilene, Texas data center"). 3 to 120 characters. |
| `kind` | `data_center`, `fab`, `plant`, `power`, `gpu_cluster`, `cloud_commitment`, `network`, `other`. |
| `status` | `announced` (stated, not yet building), `under_construction`, `in_service` (operating, energized, delivered), `contracted` (a signed agreement or commitment: PPA, lease, purchase), `cancelled`. |
| `location` | Place as stated, or null. |
| `counterparty` | The other party when stated (a tenant, a customer, a supplier, a utility), or null. |
| `amount_low`, `amount_high` | Dollar size stated for the project, whole US dollars, both the same for a single figure; omit both when none is stated. |
| `capacity_mw` | Megawatts when stated (1 GW = 1000), or null. |
| `gpus` | Number of GPUs or accelerators when stated, or null. |
| `announced`, `in_service` | Dates when stated (YYYY, YYYY-MM or YYYY-MM-DD), or null. Expected in-service dates count. |
| `quote` | One complete sentence copied verbatim from the passage, and `passage` its tag (`p03`). Code checks the quote is in the passage; a quote that is not there is rejected and the task asked again. |
| `confidence` | 0 to 1. |

## Rules

1. One row per project per text. A sentence that names two projects gives two rows, same quote.
2. Never compute or infer a size, date or status. If the text does not say, leave the field null.
3. A company total ("$10 billion of capex for data centers") is not a project unless it is tied to a named thing.
4. Keep the company's own name for the project so the same project is recognised across texts.

## Output

Return only one JSON object matching `agents/schemas/projects@v1.json`:

```json
{"accession": "META|earnings_release|2025-09-30|ab12cd34", "prompt_version": "projects@v1",
 "projects": [{"name": "Hyperion", "kind": "data_center", "status": "under_construction", "location": "Richland Parish, Louisiana", "counterparty": null,
               "amount_low": null, "amount_high": null, "capacity_mw": 2000, "gpus": null, "announced": "2024-12", "in_service": "2030",
               "quote": "Hyperion, our data center in Louisiana, will scale to 2 GW by 2030.", "passage": "p04", "confidence": 0.9}]}
```

`projects` may be empty.
