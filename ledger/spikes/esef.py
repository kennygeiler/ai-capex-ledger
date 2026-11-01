"""ESEF inline XBRL reader (T44 spike). Standard library only; not wired into the pipeline; no schema change.

An ESEF annual report is one XHTML file with the tagged numbers inline (`ix:nonFraction`) and the contexts and units in
`ix:header`. This reads the same (concept, period, unit) -> value shape that ledger/reference/dimensions.py reads from an
EDGAR instance, so a later source (T45) can hand either to the same tie rules. Differences from an EDGAR instance that the
reader has to handle, found on ASML's 2025 report: the displayed text is scaled (`scale="6"` means millions) and formatted
(`ixt:num-dot-decimal` thousands separators, `ixt:fixed-zero` for a dash), the sign lives in `sign="-"` and never in the
text, and a fact's position in the document (its page) matters because the untagged tables beside it are cited by page.

Spike-level: no inline footnotes, no `ix:continuation` stitching, no `ixt:num-comma-decimal`; a format the reader does
not know is left as text under `value: None` so nothing is guessed."""
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

IX = "{http://www.xbrl.org/2013/inlineXBRL}"
XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"
XHTML = "{http://www.w3.org/1999/xhtml}"

KNOWN_FORMATS = {None, "ixt:num-dot-decimal", "ixt:fixed-zero"}  # the two ixt 2022 names ASML's 2025 report uses


def load(source) -> ET.Element:
    """The document root, from a path or from XHTML text/bytes."""
    if isinstance(source, Path):
        return ET.parse(source).getroot()
    if isinstance(source, str) and not source.lstrip().startswith("<"):
        return ET.parse(source).getroot()
    return ET.fromstring(source if isinstance(source, bytes) else source.encode())


def contexts(root: ET.Element) -> dict:
    """context id -> (period, members): period 'YYYY-MM-DD' for an instant, 'start/end' for a duration; members a tuple of
    'Axis=Member' strings, empty for the consolidated entity."""
    out = {}
    for ctx in root.iter(f"{XBRLI}context"):
        p = ctx.find(f"{XBRLI}period")
        inst, s, e = p.find(f"{XBRLI}instant"), p.find(f"{XBRLI}startDate"), p.find(f"{XBRLI}endDate")
        period = inst.text.strip() if inst is not None else f"{s.text.strip()}/{e.text.strip()}"
        members = tuple(f"{m.get('dimension')}={m.text.strip()}" for m in ctx.iter(f"{XBRLDI}explicitMember"))
        out[ctx.get("id")] = (period, members)
    return out


def units(root: ET.Element) -> dict:
    """unit id -> measure text ('iso4217:EUR', 'xbrli:shares', 'iso4217:EUR/xbrli:shares' for a divide)."""
    out = {}
    for u in root.iter(f"{XBRLI}unit"):
        div = u.find(f"{XBRLI}divide")
        if div is not None:
            num = div.find(f"{XBRLI}unitNumerator/{XBRLI}measure").text.strip()
            den = div.find(f"{XBRLI}unitDenominator/{XBRLI}measure").text.strip()
            out[u.get("id")] = f"{num}/{den}"
        else:
            out[u.get("id")] = u.find(f"{XBRLI}measure").text.strip()
    return out


def parse_number(text: str, fmt: str | None, scale: str | None, sign: str | None):
    """The fact's value in whole units, or None when the format is not one the reader knows. A dash or an empty text is
    zero only when the filer says so with ixt:fixed-zero; otherwise it is None, never a made-up 0."""
    if fmt not in KNOWN_FORMATS:
        return None
    if fmt == "ixt:fixed-zero":
        return Decimal(0)
    t = text.strip()
    if t in ("", "-", "—", "–"):
        return None
    try:
        n = Decimal(t.replace(",", "").replace(" ", ""))
    except InvalidOperation:
        return None
    n = n * (Decimal(10) ** int(scale or 0))
    return -n if sign == "-" else n


def facts(root: ET.Element) -> dict:
    """{(concept, period, unit, members): {value, scale, decimals, text, id, context, duplicates}} for every ix:nonFraction.
    `value` is a Decimal in whole units with the sign applied (None when the format is unknown); `text` is as displayed.
    The same fact tagged more than once (a number shown on two pages) keeps the first and lists the others under
    `duplicates` as (id, value); `conflicts(facts)` names the keys whose repeats disagree, so nothing is kept silently."""
    ctx, uni = contexts(root), units(root)
    out = {}
    for el in root.iter(f"{IX}nonFraction"):
        period, members = ctx[el.get("contextRef")]
        text = "".join(el.itertext())
        key = (el.get("name"), period, uni[el.get("unitRef")], members)
        value = parse_number(text, el.get("format"), el.get("scale"), el.get("sign"))
        if key in out:
            out[key]["duplicates"].append((el.get("id"), value))
            continue
        out[key] = {
            "value": value,
            "scale": int(el.get("scale") or 0),
            "decimals": el.get("decimals"),
            "text": text,
            "id": el.get("id"),
            "context": el.get("contextRef"),
            "duplicates": [],
        }
    return out


def conflicts(all_facts: dict) -> dict:
    """{key: [(id, value), ...]} for every fact whose repeated tags do not all carry the kept value."""
    return {k: [(f["id"], f["value"])] + f["duplicates"] for k, f in all_facts.items()
            if any(v != f["value"] for _, v in f["duplicates"])}


def fact_pages(root: ET.Element, page_class: str = "pageView") -> dict:
    """fact id -> 1-based ordinal of the page element (`div class="pageView"`, Workiva's ESEF layout) that holds it. The
    ordinal equals the printed page number on ASML's 2025 report; a reader must check that on each new document."""
    out = {}
    n = 0
    for div in root.iter(f"{XHTML}div"):
        if page_class in (div.get("class") or "").split():
            n += 1
            for el in div.iter(f"{IX}nonFraction"):
                out.setdefault(el.get("id"), n)
    return out


def select(all_facts: dict, concept: str, period: str, unit: str = "iso4217:EUR") -> dict | None:
    """The consolidated (no dimension) fact for one concept and period, or None."""
    return all_facts.get((concept, period, unit, ()))
