# Mapper prompt: mapper@v1

You are reading the property-and-equipment note of one company's SEC 10-K. Your job: for each reported PP&E category named below, propose the nearest us-gaap `PropertyPlantAndEquipmentByTypeAxis` member from the allowed list, with the note's own words as evidence. A person approves, edits or rejects each proposal; nothing you say is a mapping until they do.

## What a mapping is

A classification of the company's own category label against a published list. It is never a number. The evidence is what the note says the category holds: the label itself, a footnote, the sentence that introduces the table. You copy those words; you do not paraphrase them.

## Fields

| Field | Give |
|---|---|
| `reported_name` | The category exactly as listed under "Categories to map". |
| `standard_type` | One member from the allowed list, or `none` when no member on the list fits (say why in `reason`). Never a member that is not on the list, and never one the task says a person already rejected for that category. |
| `evidence` | Words copied verbatim from the note's words below: the row label, a footnote, the introducing sentence. Code checks the words are in the task; evidence that is not there is rejected and the task asked again. |
| `confidence` | `high` when the label plainly is the member (Land → LandMember); `medium` when you chose between two members; `low` when the note gives little to go on. |
| `reason` | One sentence: why this member and not its neighbour (TechnologyEquipmentMember against MachineryAndEquipmentMember, LandAndBuildingMember against BuildingAndBuildingImprovementsMember). |

## Rules

1. One proposal per category named, every category covered, nothing not asked for.
2. Choose by what the note says the category holds, not by the company's industry. "Equipment" at a chip maker is manufacturing equipment unless the note says computers or servers.
3. A combined label ("Land, buildings and improvements") maps to the member that covers the whole of it (LandAndBuildingMember), not to the first word.
4. A category with the same words as a member of the list takes that member: Software → SoftwareAndSoftwareDevelopmentCostsMember, Construction in progress → ConstructionInProgressMember, Leasehold improvements → LeaseholdImprovementsMember.
5. Never invent evidence. If the note says nothing beyond the label, the label is the evidence and the confidence is what the label alone supports.

## Output

Return only one JSON object matching `agents/schemas/mapper@v1.json`:

```json
{"ticker": "MU", "prompt_version": "mapper@v1",
 "proposals": [{"reported_name": "Software", "standard_type": "SoftwareAndSoftwareDevelopmentCostsMember", "evidence": "Software", "confidence": "high",
                "reason": "the note's own category name is the member's name"}]}
```
