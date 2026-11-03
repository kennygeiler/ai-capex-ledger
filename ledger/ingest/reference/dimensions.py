"""Dimensional facts from a filing's own XBRL instance: the answer key for the note facts.

companyfacts carries company totals only. Segment capex, segment revenue and PP&E by category are tagged in the
instance with one dimension member each (StatementBusinessSegmentsAxis, ProductOrServiceAxis,
PropertyPlantAndEquipmentByTypeAxis), so the instance is read directly. Balances come from instant contexts."""
import json
import xml.etree.ElementTree as ET

from ..edgar import RAW, _cached
from .xbrl_instance import XBRLI, _instance_name

XBRLDI = "{http://xbrl.org/2006/xbrldi}"
GAAP = "{http://fasb.org/us-gaap/"

# Concepts tried per field, in order. Members are matched by name (ledger.extract.notes.norm_dim), never by axis.
CONCEPTS = {
    "segment_capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets", "PropertyPlantAndEquipmentAdditions",
                      "NoncashOrPartNoncashAcquisitionFixedAssetsAcquired1"],
    "segment_revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "ppe_category": ["PropertyPlantAndEquipmentGross"],
    "finance_lease_liability": ["FinanceLeaseLiability"],
    "purchase_commitments": ["PurchaseObligation", "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", "UnrecordedUnconditionalPurchaseObligation"],
    # not ContractualObligation: it is the total of every contractual obligation (debt, leases, purchases), a wider line;
    # Amazon's FY2024 and FY2025 10-Ks tag only that total, and the fallback made a right cell look wrong (type 71)
}


def instance_facts(cik: int, accession: str) -> dict:
    """{(concept, member or '', end date): value} for USD facts with at most one dimension; a duration fact only when
    it spans a fiscal year (350–380 days). Empty when the filing has no instance XML."""
    distilled = RAW / f"{cik:010d}" / "filings" / f"{accession}.facts.json"  # the facts this function returns, kept so the XML is read once; the golden fixtures carry only this
    if distilled.exists():
        return {tuple(k.split("\t")): v for k, v in json.loads(distilled.read_text()).items()}
    url = _instance_name(cik, accession)
    if not url:
        return {}
    body, _ = _cached(url, RAW / f"{cik:010d}" / "filings" / f"{accession}.xml", False, 24 * 365)
    root = ET.fromstring(body)
    contexts = {}
    for ctx in root.iter(f"{XBRLI}context"):
        # a dimension may sit under <segment> or <scenario> (T92 review): either way the context is not a company total
        boxes = [b for b in (ctx.find(f"{XBRLI}entity/{XBRLI}segment"), ctx.find(f"{XBRLI}scenario")) if b is not None]
        dims = [d for b in boxes for d in b]
        members = [d.text.strip() for d in dims if d.tag == f"{XBRLDI}explicitMember" and d.text]
        if dims and (len(members) != 1 or len(dims) != 1):
            continue  # typed or multi-dimensional: not a plain segment or category breakdown, and never a total
        p = ctx.find(f"{XBRLI}period")
        inst, s, e = p.find(f"{XBRLI}instant"), p.find(f"{XBRLI}startDate"), p.find(f"{XBRLI}endDate")
        if inst is not None:
            contexts[ctx.get("id")] = (members[0] if members else "", inst.text.strip())
        elif s is not None and e is not None:
            from datetime import date
            days = (date.fromisoformat(e.text.strip()) - date.fromisoformat(s.text.strip())).days + 1
            if 350 <= days <= 380:
                contexts[ctx.get("id")] = (members[0] if members else "", e.text.strip())
    usd = {u.get("id") for u in root.iter(f"{XBRLI}unit")
           if (m := u.find(f"{XBRLI}measure")) is not None and m.text and m.text.strip().lower().endswith(":usd")}
    out = {}
    for el in root:
        if not el.tag.startswith(GAAP) or el.get("contextRef") not in contexts or el.get("unitRef") not in usd or not el.text:
            continue
        try:
            val = round(float(el.text.strip()))
        except ValueError:
            continue
        member, end = contexts[el.get("contextRef")]
        out.setdefault((el.tag.split("}", 1)[1], member, end), val)
    distilled.parent.mkdir(parents=True, exist_ok=True)
    distilled.write_text(json.dumps({"\t".join(k): v for k, v in out.items()}))
    return out
