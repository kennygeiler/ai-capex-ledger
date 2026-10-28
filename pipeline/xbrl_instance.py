"""Fallback: parse a filing's XBRL instance XML directly.

SEC's companyfacts API can lag behind new filings. When a 10-Q/10-K is on EDGAR but none of its periods
appear in companyfacts, we fetch the filing's extracted XBRL instance (the *_htm.xml next to the inline-XBRL
document) and read the facts ourselves: contexts give the period, units give the currency, and facts with a
dimensional segment (business-segment breakdowns) are skipped so only company totals are kept.
"""
import json
import xml.etree.ElementTree as ET

from .edgar import RAW, _cached

XBRLI = "{http://www.xbrl.org/2003/instance}"


def _instance_name(cik: int, accn: str) -> str | None:
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}"
    body, _ = _cached(f"{base}/index.json", RAW / f"{cik:010d}" / "filings" / f"{accn}.index.json", False, 24 * 365)
    items = [i["name"] for i in json.loads(body)["directory"]["item"]]
    xml = [n for n in items if n.endswith("_htm.xml")] or [n for n in items if n.endswith(".xml") and not n.startswith("Financial") and "_" not in n[-8:]]
    return f"{base}/{xml[0]}" if xml else None


def parse_instance(xml_bytes: bytes, accn: str, form: str, filed: str) -> dict[str, list[dict]]:
    """Return {us-gaap concept: [fact dicts shaped like companyfacts USD units]} for non-dimensional USD facts."""
    root = ET.fromstring(xml_bytes)
    contexts = {}
    for ctx in root.iter(f"{XBRLI}context"):
        if ctx.find(f"{XBRLI}entity/{XBRLI}segment") is not None:
            continue  # dimensional (segment) context: not a company total
        p = ctx.find(f"{XBRLI}period")
        s, e = p.find(f"{XBRLI}startDate"), p.find(f"{XBRLI}endDate")
        if s is not None and e is not None:
            contexts[ctx.get("id")] = (s.text.strip(), e.text.strip())
    usd_units = {u.get("id") for u in root.iter(f"{XBRLI}unit")
                 if (m := u.find(f"{XBRLI}measure")) is not None and m.text and m.text.strip().lower().endswith(":usd")}
    out: dict[str, list[dict]] = {}
    for el in root:
        tag = el.tag
        if not tag.startswith("{http://fasb.org/us-gaap/"):
            continue
        ctx, unit = el.get("contextRef"), el.get("unitRef")
        if ctx not in contexts or unit not in usd_units or el.text is None or el.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
            continue
        try:
            val = round(float(el.text.strip()))
        except ValueError:
            continue
        start, end = contexts[ctx]
        out.setdefault(tag.split("}", 1)[1], []).append(
            {"start": start, "end": end, "val": val, "accn": accn, "form": form, "filed": filed, "src": "xbrl_instance"})
    # one fact per (concept, period): duplicates in an instance carry the same value
    for k, vals in out.items():
        out[k] = list({(v["start"], v["end"]): v for v in vals}.values())
    return out


def fill_gaps(cf: dict, cik: int, filings: list[dict], since: str) -> list[dict]:
    """Parse instance XML for periodic filings that companyfacts doesn't cover yet; merge into cf in place."""
    gaap = cf.setdefault("facts", {}).setdefault("us-gaap", {})
    have_ends = {x.get("end") for node in gaap.values() for vals in node.get("units", {}).values() for x in vals}
    added = []
    for f in filings:
        if f["form"] not in ("10-Q", "10-K") or not f["period"] or f["period"] < since or f["period"] in have_ends:
            continue
        url = _instance_name(cik, f["accession"])
        if not url:
            added.append({"accession": f["accession"], "period": f["period"], "status": "no instance XML found"})
            continue
        body, _ = _cached(url, RAW / f"{cik:010d}" / "filings" / f"{f['accession']}.xml", False, 24 * 365)
        facts = parse_instance(body, f["accession"], f["form"], f["filed"])
        for concept, vals in facts.items():
            gaap.setdefault(concept, {"label": concept, "units": {}}).setdefault("units", {}).setdefault("USD", []).extend(vals)
        added.append({"accession": f["accession"], "form": f["form"], "period": f["period"], "filed": f["filed"], "url": url,
                      "concepts": len(facts), "facts": sum(len(v) for v in facts.values()), "status": "parsed"})
    return added
