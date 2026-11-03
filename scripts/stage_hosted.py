"""Stage the stored 10-K filings the hosted copy needs into deploy/raw/ before `railway up`.

data/raw (several GB) is never uploaded. The hosted copy still needs the primary document of every filing in scope:
the crop state and the in-app viewer hash the stored filing against documents.sha256. This copies exactly those files
(data/raw/<cik>/docs/<accession>.htm) into deploy/raw/, which the Dockerfile layers over data/raw.

    uv run python scripts/stage_hosted.py && railway up --service datahq
"""

import shutil
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ledger.core import config  # noqa: E402


def main() -> None:
    out = ROOT / "deploy" / "raw"
    if out.exists():
        shutil.rmtree(out)
    con = duckdb.connect(str(ROOT / "data" / "ledger.duckdb"), read_only=True)
    rows = con.execute("select distinct cik, accession from documents where ticker in (select unnest(?))",
                       [list(config.PROVEN)]).fetchall()
    missing, n, size = [], 0, 0
    for cik, acc in rows:
        rel = Path(f"{int(cik):010d}") / "docs" / f"{acc}.htm"
        src = ROOT / "data" / "raw" / rel
        if not src.is_file():
            missing.append(str(rel))
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n, size = n + 1, size + src.stat().st_size
    print(f"staged {n} of {len(rows)} filings, {size / 1e6:.1f} MB, in deploy/raw")
    if missing:
        raise SystemExit("missing stored filings: " + ", ".join(missing))


if __name__ == "__main__":
    main()
