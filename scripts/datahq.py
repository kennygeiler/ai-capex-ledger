"""Export DATAHQ's numbers to reports/datahq/*.json, for the DATAHQ dashboard artifact (the app reads them live)."""
import json

from ledger import store
from ledger.hq import snapshot

OUT = store.ROOT / "reports" / "datahq"

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in snapshot(store.init(str(store.DEFAULT_DB))).items():
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=1, default=str))
    print(f"wrote {OUT.relative_to(store.ROOT)}/")
