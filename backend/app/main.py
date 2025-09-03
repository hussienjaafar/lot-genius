from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Optional

import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy arrays and types."""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)


from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

# dual import fallback for local vs package layout
try:
    from lotgenius.api.ebay_compliance import router as ebay_router
    from lotgenius.api.schemas import ReportRequest
    from lotgenius.api.service import (
        generate_report,
        report_stream,
        run_optimize,
        run_pipeline,
        save_upload_temp,
    )
except ModuleNotFoundError:
    from backend.lotgenius.api.ebay_compliance import (
        router as ebay_router,  # type: ignore
    )
    from backend.lotgenius.api.schemas import ReportRequest  # type: ignore
    from backend.lotgenius.api.service import (  # type: ignore
        generate_report,
        report_stream,
        run_optimize,
        run_pipeline,
        save_upload_temp,
    )

app = FastAPI(title="LotGenius API")

# Add CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
        "http://localhost:3004",
        "http://127.0.0.1:3004",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include eBay compliance endpoints for production API access
app.include_router(ebay_router)


# Additional root-level endpoint for eBay in case they expect no prefix
@app.get("/marketplace-account-deletion")
async def root_ebay_verification(challenge_code: str):
    """Root-level eBay marketplace account deletion endpoint"""
    print(f"Root eBay verification - challenge_code: {challenge_code}")
    return {"challengeResponse": challenge_code}


# PLAIN TEXT VERSION - Most likely what eBay actually wants
@app.get("/marketplace-account-deletion-plain")
async def root_ebay_verification_plain(challenge_code: str):
    """Root-level eBay endpoint returning plain text"""
    print(f"Root eBay PLAIN TEXT verification - challenge_code: {challenge_code}")
    return PlainTextResponse(content=challenge_code)


def _sse(event_dict: dict) -> str:
    """Format a Server-Sent Event with both 'event:' and 'data:' lines."""
    name = event_dict.get("event") or "message"
    return f"event: {name}\n" f"data: {json.dumps(event_dict, cls=NumpyEncoder)}\n\n"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default


def check_api_key(request: Request) -> None:
    """Check API key if LOTGENIUS_API_KEY is set in environment."""
    expected_key = os.environ.get("LOTGENIUS_API_KEY")
    if not expected_key:
        # No API key configured, allow open access
        return

    provided_key = request.headers.get("X-API-Key")
    if not provided_key or provided_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/v1/report")
async def report_endpoint(request: Request) -> Response:
    """Generate report (blocking)."""
    check_api_key(request)

    try:
        body = await request.json()
        req = ReportRequest(**body)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        response = generate_report(req)
        return Response(
            content=json.dumps(response.model_dump()),
            media_type="application/json",
            status_code=200,
        )
    except FileNotFoundError as e:
        # Return 404 for file not found errors
        error_msg = str(e)
        if "not found" not in error_msg.lower():
            error_msg = f"File not found: {error_msg}"
        raise HTTPException(status_code=404, detail=error_msg)
    except ValueError as e:
        # Return 400 for missing opt_json
        error_msg = str(e)
        if "must be provided" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/report/stream")
async def report_stream_endpoint(request: Request) -> Response:
    """Generate report (SSE stream)."""
    check_api_key(request)

    try:
        body = await request.json()
        req = ReportRequest(**body)
    except Exception:
        # Return error as SSE event for stream endpoint
        def error_gen():
            yield _sse({"event": "error", "status": "error", "detail": str(e)})

        return StreamingResponse(
            error_gen(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    def gen():
        try:
            # Start event
            yield _sse({"event": "start", "message": "Starting report generation"})

            # Generate markdown stage
            yield _sse(
                {"event": "generate_markdown", "message": "Generating markdown report"}
            )

            # Use the report_stream generator from service
            for event in report_stream(req):
                yield _sse(event)

            # Done event
            yield _sse(
                {
                    "event": "done",
                    "status": "ok",
                    "message": "Report generation complete",
                }
            )

        except FileNotFoundError as e:
            yield _sse(
                {
                    "event": "error",
                    "status": "error",
                    "detail": f"File not found: {str(e)}",
                }
            )
        except ValueError as e:
            yield _sse({"event": "error", "status": "error", "detail": str(e)})
        except Exception as e:
            yield _sse({"event": "error", "status": "error", "detail": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@app.post("/v1/optimize/upload")
async def optimize_upload(request: Request) -> Response:
    """Optimize upload (blocking, multipart)."""
    check_api_key(request)

    form = await request.form()
    items_file = form.get("items_csv")
    if not items_file:
        raise HTTPException(status_code=400, detail="items_csv file is required")

    opt_file: Optional[UploadFile] = form.get("opt_json")  # type: ignore
    opt_inline: Optional[str] = form.get("opt_json_inline")  # type: ignore

    if not opt_file and not opt_inline:
        raise HTTPException(
            status_code=400,
            detail="opt_json (file) or opt_json_inline (JSON) is required",
        )

    try:
        # Save uploaded files
        items_path = save_upload_temp(items_file, suffix=".csv")

        opt_json_path: Optional[str] = None
        if opt_file is not None:
            opt_json_path = str(save_upload_temp(opt_file, suffix=".json"))
        elif opt_inline:
            # Validate and save inline JSON
            try:
                parsed = json.loads(opt_inline)
            except Exception:
                items_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400, detail="opt_json_inline must be valid JSON"
                )

            tmp = Path(items_path.parent / (items_path.stem + ".opt.json"))
            tmp.write_text(json.dumps(parsed), encoding="utf-8")
            opt_json_path = str(tmp)

        # Run optimizer
        result, _ = run_optimize(str(items_path), opt_json_path)

        # Clean up temp files
        try:
            items_path.unlink(missing_ok=True)
            if opt_json_path:
                Path(opt_json_path).unlink(missing_ok=True)
        except Exception:
            pass

        return Response(
            content=json.dumps({"status": "ok", "summary": result}),
            media_type="application/json",
            status_code=200,
        )

    except Exception as e:
        # Clean up on error
        try:
            if "items_path" in locals():
                items_path.unlink(missing_ok=True)
            if "opt_json_path" in locals() and opt_json_path:
                Path(opt_json_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.options("/v1/optimize/upload/stream")
async def optimize_upload_stream_options():
    """Handle CORS preflight for optimize upload endpoint."""
    return Response(status_code=200)


@app.post("/v1/optimize/upload/stream")
async def optimize_upload_stream(request: Request) -> Response:
    """Optimize upload (SSE stream)."""
    check_api_key(request)

    form = await request.form()
    items_file = form.get("items_csv")
    if not items_file:

        def error_gen():
            yield _sse(
                {
                    "event": "error",
                    "status": "error",
                    "detail": "items_csv file is required",
                }
            )

        return StreamingResponse(
            error_gen(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    opt_file: Optional[UploadFile] = form.get("opt_json")  # type: ignore
    opt_inline: Optional[str] = form.get("opt_json_inline")  # type: ignore

    if not opt_file and not opt_inline:

        def error_gen():
            yield _sse(
                {
                    "event": "error",
                    "status": "error",
                    "detail": "opt_json (file) or opt_json_inline (JSON) is required",
                }
            )

        return StreamingResponse(
            error_gen(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    # Save uploaded files
    items_path = save_upload_temp(items_file, suffix=".csv")

    opt_json_path: Optional[str] = None
    if opt_file is not None:
        opt_json_path = str(save_upload_temp(opt_file, suffix=".json"))
    elif opt_inline:
        try:
            parsed = json.loads(opt_inline)
        except Exception:
            items_path.unlink(missing_ok=True)

            def error_gen():
                yield _sse(
                    {
                        "event": "error",
                        "status": "error",
                        "detail": "opt_json_inline must be valid JSON",
                    }
                )

            return StreamingResponse(
                error_gen(),
                media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no"},
            )

        tmp = Path(items_path.parent / (items_path.stem + ".opt.json"))
        tmp.write_text(json.dumps(parsed), encoding="utf-8")
        opt_json_path = str(tmp)

    def gen():
        try:
            # Start event
            yield _sse({"event": "start", "message": "Starting optimization"})

            # Optimize event
            yield _sse({"event": "optimize", "message": "Running optimizer"})

            # Run optimizer
            result, _ = run_optimize(str(items_path), opt_json_path)

            # Done event with result
            yield _sse(
                {
                    "event": "done",
                    "status": "ok",
                    "message": "Optimization complete",
                    "summary": result,
                }
            )

        except Exception as e:
            yield _sse({"event": "error", "status": "error", "detail": str(e)})
        finally:
            # Clean up temp files
            try:
                items_path.unlink(missing_ok=True)
                if opt_json_path:
                    Path(opt_json_path).unlink(missing_ok=True)
            except Exception:
                pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@app.post("/v1/pipeline/upload")
async def pipeline_upload(request: Request) -> Response:
    """Pipeline upload (blocking, multipart)."""
    check_api_key(request)

    form = await request.form()
    items_file = form.get("items_csv")
    if not items_file:
        raise HTTPException(status_code=400, detail="items_csv file is required")

    opt_file: Optional[UploadFile] = form.get("opt_json")  # type: ignore
    opt_inline: Optional[str] = form.get("opt_json_inline")  # type: ignore

    try:
        # Save uploaded files
        items_path = save_upload_temp(items_file, suffix=".csv")

        opt_json_path: Optional[str] = None
        if opt_file is not None:
            opt_json_path = str(save_upload_temp(opt_file, suffix=".json"))
        elif opt_inline:
            # Validate and save inline JSON
            try:
                parsed = json.loads(opt_inline)
            except Exception:
                items_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400, detail="opt_json_inline must be valid JSON"
                )

            tmp = Path(items_path.parent / (items_path.stem + ".opt.json"))
            tmp.write_text(json.dumps(parsed), encoding="utf-8")
            opt_json_path = str(tmp)

        # Handle optional stress files
        stress_csv_path: Optional[str] = None
        stress_json_path: Optional[str] = None
        stress_csv_file = form.get("stress_csv")
        stress_json_file = form.get("stress_json")

        if stress_csv_file:
            stress_csv_path = str(save_upload_temp(stress_csv_file, suffix=".csv"))
        if stress_json_file:
            stress_json_path = str(save_upload_temp(stress_json_file, suffix=".json"))

        # Run pipeline (without SSE yield)
        result = run_pipeline(
            str(items_path),
            opt_json_path,
            None,  # out_markdown
            None,  # out_html
            None,  # out_pdf
            stress_csv=stress_csv_path,
            stress_json=stress_json_path,
            sse_yield=None,  # No streaming for blocking endpoint
        )

        # Extract phases and markdown preview from result
        phases = result.get("phases", []) if isinstance(result, dict) else []
        markdown_preview = (
            result.get("markdown_preview", "") if isinstance(result, dict) else ""
        )

        # Clean up temp files
        try:
            items_path.unlink(missing_ok=True)
            if opt_json_path:
                Path(opt_json_path).unlink(missing_ok=True)
            if stress_csv_path:
                Path(stress_csv_path).unlink(missing_ok=True)
            if stress_json_path:
                Path(stress_json_path).unlink(missing_ok=True)
        except Exception:
            pass

        return Response(
            content=json.dumps(
                {"status": "ok", "phases": phases, "markdown_preview": markdown_preview}
            ),
            media_type="application/json",
            status_code=200,
        )

    except Exception as e:
        # Clean up on error
        try:
            if "items_path" in locals():
                items_path.unlink(missing_ok=True)
            if "opt_json_path" in locals() and opt_json_path:
                Path(opt_json_path).unlink(missing_ok=True)
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/pipeline/upload/stream")
async def pipeline_upload_stream(request: Request) -> Response:
    """
    Multipart fields:
      - items_csv: UploadFile (required)
      - opt_json: UploadFile (optional)
      - opt_json_inline: str (optional JSON)
    Streams SSE phases and finishes with {type: "final_summary", payload: {...}}.
    """
    check_api_key(request)

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
    items_file = form.get("items_csv")
    if not items_file:
        return Response(
            content=json.dumps({"detail": "items_csv file is required"}),
            media_type="application/json",
            status_code=400,
        )

    # Ensure items_file is an UploadFile, not a string
    if isinstance(items_file, str):
        return Response(
            content=json.dumps(
                {"detail": "items_csv must be a file upload, not a string"}
            ),
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

    # Handle optional stress files
    stress_csv_path: Optional[str] = None
    stress_json_path: Optional[str] = None
    stress_csv_file = form.get("stress_csv")
    stress_json_file = form.get("stress_json")

    if stress_csv_file:
        stress_csv_path = str(save_upload_temp(stress_csv_file, suffix=".csv"))
    if stress_json_file:
        stress_json_path = str(save_upload_temp(stress_json_file, suffix=".json"))

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
                try:
                    if SIMULATE_SLOW_MS:
                        time.sleep(SIMULATE_SLOW_MS / 1000.0)
                    res = run_pipeline(
                        str(items_path),
                        opt_json_path,
                        None,
                        None,
                        None,
                        stress_csv=stress_csv_path,
                        stress_json=stress_json_path,
                        sse_yield=sse_push,
                    )
                    final_payload = res if isinstance(res, dict) else {"result": res}
                except Exception as e:
                    # Emit error event from worker thread
                    error_text = str(e)
                    # Truncate to fit within 200 chars including prefix
                    max_error_len = 200 - len("Pipeline error: ")
                    if len(error_text) > max_error_len:
                        error_text = error_text[:max_error_len]
                    sse_push(
                        {
                            "event": "error",
                            "status": "error",
                            "message": f"Pipeline error: {error_text}",
                        }
                    )
                finally:
                    done["flag"] = True

            th = threading.Thread(target=worker, daemon=True)
            th.start()

            # Stream events as they arrive; emit heartbeat pings if idle
            error_occurred = False
            while True:
                try:
                    ev = q.get(timeout=HEARTBEAT_SEC)
                    yield _sse(ev)
                    # Check if this is an error event
                    if ev.get("event") == "error":
                        error_occurred = True
                except Empty:
                    # Continue heartbeat until done or error
                    if not done["flag"]:
                        yield _sse({"event": "ping", "ts": time.time()})

                if done["flag"] and q.empty():
                    break

            # Final frame - only send "done" if no error occurred
            if not error_occurred:
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
            if stress_csv_path:
                try:
                    Path(stress_csv_path).unlink(missing_ok=True)
                except Exception:
                    pass
            if stress_json_path:
                try:
                    Path(stress_json_path).unlink(missing_ok=True)
                except Exception:
                    pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )
