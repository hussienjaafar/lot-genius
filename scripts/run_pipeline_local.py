import json
from pathlib import Path

from backend.lotgenius.api.service import run_pipeline


def main(csv_path: str, opt_json_path: str | None = None):
    csv = Path(csv_path)
    assert csv.exists(), f"CSV not found: {csv}"

    if opt_json_path is None:
        tmp = Path("data/api/tmp/local.opt.json")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"roi_target": 1.25, "risk_threshold": 0.8}), encoding="utf-8")
        opt_json_path = str(tmp)

    res = run_pipeline(str(csv), opt_json_path, None, None, None)
    print(json.dumps({"phases": res.get("phases"), "ok": True}, indent=2))


if __name__ == "__main__":
    import sys

    csv = sys.argv[1] if len(sys.argv) > 1 else "test_manifest_5_items.csv"
    main(csv)
