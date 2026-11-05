"""python -m ledger signoff <version> --by "<name>"   ->  releases/<version>/SIGNOFF.json

The Release page signs through `sign()` too (checklist.sign), and passes the checklist as it was at signing, so
SIGNOFF.json says what the signature meant (T6, T7). The command line records none: a signature from here carries
only who, when and the hash. Either way the name must be on config.PEOPLE (F18), and the command passes the same gate
as the page's Sign first (checklist.preflight): no uncommitted code, and the run lines bound to this checkout."""
import argparse
import json
from datetime import datetime, timezone

from ..release.release import RELEASES, content_hash


def sign(version: str, by: str, checklist: dict | None = None) -> dict:
    """Write SIGNOFF.json for a built release whose files still match their hash; raise ValueError otherwise. `by` must
    be a person on config.PEOPLE (status.is_person, F18), from the command line and the page alike: checked first."""
    from ..core.status import is_person
    if not is_person(by):
        raise ValueError(f"{str(by or '').strip()!r} is not on config.PEOPLE, the people who may sign a release; not signed.")
    by = by.strip()
    d = RELEASES / version
    if not (d / "manifest.json").exists():
        raise ValueError(f"no release {version}")
    if (d / "SIGNOFF.json").exists():
        raise ValueError(f"{version} is already signed; a signature is never replaced")
    m = json.loads((d / "manifest.json").read_text())
    files = {n: (d / n).open(newline="").read() for n in m["files"]}  # exact bytes: the hash was taken before the write
    h = m["hash"]
    if content_hash(files) != h:
        raise ValueError(f"{version} files no longer match their hash; not signed.")
    s = {"version": version, "hash": h, "signed_by": by, "signed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if checklist is not None:
        s["checklist"] = checklist
    (d / "SIGNOFF.json").write_text(json.dumps(s, indent=1))
    return s


def record(version: str, **fields) -> dict:
    """Add fields to a release's SIGNOFF.json after the signature: the publish's outcome (published, published_at, rows,
    or publish_error). The signed fields and the checklist never change."""
    f = RELEASES / version / "SIGNOFF.json"
    s = json.loads(f.read_text())
    for k in ("version", "hash", "signed_by", "signed_at", "checklist"):
        fields.pop(k, None)
    s.update(fields)
    f.write_text(json.dumps(s, indent=1))
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger signoff")
    ap.add_argument("version")
    ap.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    from ..release.checklist import preflight
    try:
        preflight()  # the page's Sign gate: no uncommitted code, and the Regression test and Test run lines pass on this checkout
        s = sign(a.version, a.by)
    except ValueError as e:
        print(e)
        return 1
    print(f"{a.version} signed by {s['signed_by']} ({s['hash'][:12]})")
    return 0
