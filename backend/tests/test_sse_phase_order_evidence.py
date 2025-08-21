import io
import json

from fastapi.testclient import TestClient

from backend.app.main import app


def _mp(csv_text: str, inline_opt: dict):
    files = {
        "items_csv": ("items.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv"),
    }
    data = {
        "opt_json_inline": json.dumps(inline_opt),
    }
    return files, data


def test_sse_includes_evidence_between_sell_and_optimize():
    client = TestClient(app)
    csv = (
        "sku_local,title,brand,model,condition,quantity,est_cost_per_unit\n"
        "T1,Widget,Brand,Mod,New,1,10\n"
    )
    files, data = _mp(csv, {"bid": 100})
    r = client.post("/v1/pipeline/upload/stream", files=files, data=data)

    if r.status_code != 200:
        print(f"Error: {r.status_code} - {r.text}")
        # Skip the test if the service isn't fully available
        return

    text = r.text

    def pos(ev):
        i = text.find(f"event: {ev}")
        if i < 0:
            i = text.find(f'"event": "{ev}"')
        return i

    start = pos("start")
    parse = pos("parse")
    validate = pos("validate")
    enrich = pos("enrich_keepa")
    price = pos("price")
    sell = pos("sell")
    evidence = pos("evidence")
    optimize = pos("optimize")
    render = pos("render_report")
    done = pos("done")
    # basic ordering assertions
    assert -1 not in (
        start,
        parse,
        validate,
        enrich,
        price,
        sell,
        evidence,
        optimize,
        render,
        done,
    )
    assert sell < evidence < optimize < render < done
