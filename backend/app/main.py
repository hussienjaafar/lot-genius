from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

# dual import fallback for local vs package layout
try:
    from lotgenius.api.service import run_pipeline, save_upload_temp
except ModuleNotFoundError:
    from backend.lotgenius.api.service import (  # type: ignore
        run_pipeline,
        save_upload_temp,
    )

app = FastAPI(title="LotGenius API")


def _sse(event_dict: dict) -> str:
    """Format a Server-Sent Event with both 'event:' and 'data:' lines."""
    name = event_dict.get("event") or "message"
    return f"event: {name}\n" f"data: {json.dumps(event_dict)}\n\n"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default


@app.post("/v1/pipeline/upload/stream")
async def pipeline_upload_stream(request: Request) -> Response:
    """
    Multipart fields:
      - items_csv: UploadFile (required)
      - opt_json: UploadFile (optional)
      - opt_json_inline: str (optional JSON)
    Streams SSE phases and finishes with {type: "final_summary", payload: {…}}.
    """
    # Optional per-request overrides for tests: ?hb=seconds&slow_ms=milliseconds
    hb_sec_q = request.query_params.get("hb")
    slow_ms_q = request.query_params.get("slow_ms")
    HEARTBEAT_SEC = max(
        1, min(60, int(float(hb_sec_q)) if hb_sec_q else _env_int("HEARTBEAT_SEC", 15))
    )
    SIMULATE_SLOW_MS = max(0, int(slow_ms_q)) if slow_ms_q else 0

    # Optional global size limit (default 10 MiB). Checked again after save.
    MAX_UPLOAD_BYTES = _env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
    # Early header check (best-effort; may be missing with chunked):
    try:
        cl = request.headers.get("content-length")
        if cl and int(cl) > MAX_UPLOAD_BYTES:
            return Response(
                content=json.dumps(
                    {"detail": f"Upload too large (>{MAX_UPLOAD_BYTES} bytes)"}
                ),
                media_type="application/json",
                status_code=413,
            )
    except Exception:
        pass

    form = await request.form()
    items_file: UploadFile = form.get("items_csv")  # type: ignore
    if not isinstance(items_file, UploadFile):
        return Response(
            content=json.dumps({"detail": "items_csv file is required"}),
            media_type="application/json",
            status_code=400,
        )

    opt_file: Optional[UploadFile] = form.get("opt_json")  # type: ignore
    opt_inline: Optional[str] = form.get("opt_json_inline")  # type: ignore

    items_path: Path = save_upload_temp(items_file, suffix=".csv")
    # Post-save size guard in case Content-Length was absent or wrong
    try:
        if items_path.stat().st_size > MAX_UPLOAD_BYTES:
            try:
                items_path.unlink(missing_ok=True)
            except Exception:
                pass
            return Response(
                content=json.dumps(
                    {"detail": f"Upload too large (>{MAX_UPLOAD_BYTES} bytes)"}
                ),
                media_type="application/json",
                status_code=413,
            )
    except Exception:
        pass

    opt_json_path: Optional[str] = None
    if opt_file is not None:
        opt_json_path = str(save_upload_temp(opt_file, suffix=".json"))
    elif opt_inline:
        # Validate JSON first to ensure 400 sync failure rather than mid-stream
        try:
            parsed = json.loads(opt_inline)
        except Exception:
            # Clean up CSV temp before returning error
            try:
                items_path.unlink(missing_ok=True)
            except Exception:
                pass
            return Response(
                content=json.dumps({"detail": "opt_json_inline must be valid JSON"}),
                media_type="application/json",
                status_code=400,
            )
        tmp = Path(items_path.parent / (items_path.stem + ".opt.json"))
        tmp.write_text(json.dumps(parsed), encoding="utf-8")
        opt_json_path = str(tmp)

    def gen():
        try:
            # Start (streamed immediately)
            yield _sse({"event": "start", "message": "starting pipeline(upload)"})

            q: Queue[Dict[str, Any]] = Queue()
            final_payload: Optional[Dict[str, Any]] = None
            done = {"flag": False}

            def sse_push(ev: Dict[str, Any]):
                name = ev.get("event") or ev.get("stage") or "message"
                msg = ev.get("message") or ev.get("stage") or ""
                q.put(
                    {
                        "event": name,
                        "message": msg,
                        **{
                            k: v
                            for k, v in ev.items()
                            if k not in ("event", "stage", "message")
                        },
                    }
                )

            def worker():
                nonlocal final_payload
                if SIMULATE_SLOW_MS:
                    time.sleep(SIMULATE_SLOW_MS / 1000.0)
                res = run_pipeline(
                    str(items_path),
                    opt_json_path,
                    None,
                    None,
                    None,
                    sse_yield=sse_push,
                )
                final_payload = res if isinstance(res, dict) else {"result": res}
                done["flag"] = True

            th = threading.Thread(target=worker, daemon=True)
            th.start()

            # Stream events as they arrive; emit heartbeat pings if idle
            while True:
                try:
                    ev = q.get(timeout=HEARTBEAT_SEC)
                    yield _sse(ev)
                except Empty:
                    yield _sse({"event": "ping", "ts": time.time()})

                if done["flag"] and q.empty():
                    break

            # Final frame
            yield _sse(
                {
                    "event": "done",
                    "status": "ok",
                    "type": "final_summary",
                    "payload": final_payload or {},
                }
            )
        except Exception as e:
            yield _sse({"event": "error", "status": "error", "detail": str(e)})
        finally:
            try:
                items_path.unlink(missing_ok=True)
            except Exception:
                pass
            if opt_json_path:
                try:
                    Path(opt_json_path).unlink(missing_ok=True)
                except Exception:
                    pass

    return StreamingResponse(gen(), media_type="text/event-stream")
