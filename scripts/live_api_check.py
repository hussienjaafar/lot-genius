import time
import json
import sys
from pathlib import Path

import requests


def main():
    base = "https://lot-genius.onrender.com"
    csv_path = Path(__file__).resolve().parents[1] / "realistic_liquidation_manifest.csv"
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("GET /healthz ...", end=" ")
    r = requests.get(f"{base}/healthz", timeout=20)
    print(r.status_code)

    print("GET /ebay/health ...", end=" ")
    r = requests.get(f"{base}/ebay/health", timeout=20)
    print(r.statusCode if hasattr(r, 'statusCode') else r.status_code)

    print("POST /v1/pipeline/upload ...", end=" ")
    t0 = time.time()
    with open(csv_path, "rb") as fh:
        files = {"items_csv": ("manifest.csv", fh, "text/csv")}
        data = {"opt_json_inline": json.dumps({"roi_target": 1.25, "risk_threshold": 0.8})}
        resp = requests.post(f"{base}/v1/pipeline/upload", files=files, data=data, timeout=120)
    elapsed = time.time() - t0
    print(resp.status_code, f"{elapsed:.1f}s")
    try:
        js = resp.json()
    except Exception:
        print(resp.text[:400])
        sys.exit(2)
    print(json.dumps({k: js.get(k) for k in ("status", "phases")}, indent=2))

    ok = js.get("status") == "ok" and isinstance(js.get("phases"), list)
    print("RESULT:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
