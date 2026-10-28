"""python -m ledger signoff <version> --by "<name>"   ->  releases/<version>/SIGNOFF.json"""
import argparse
import json
from datetime import datetime, timezone

from ..release import content_hash
from .release import RELEASES


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger signoff")
    ap.add_argument("version")
    ap.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    d = RELEASES / a.version
    files = {n: (d / n).read_text() for n in ("values.csv", "QUALITY.md", "DIFF.md")}
    h = json.loads((d / "manifest.json").read_text())["hash"]
    if content_hash(files) != h:
        print(f"{a.version} files no longer match their hash; not signed.")
        return 1
    (d / "SIGNOFF.json").write_text(json.dumps({"version": a.version, "hash": h, "signed_by": a.by,
                                                "signed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=1))
    print(f"{a.version} signed by {a.by} ({h[:12]})")
    return 0
