import json
import os
from typing import Generator

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from lotgenius.api.schemas import ReportRequest, ReportResponse
from lotgenius.api.service import generate_report, report_stream

# CORS configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

# Create FastAPI app
app = FastAPI(
    title="Lot Genius API",
    description="API for generating lot analysis reports",
    version="0.0.1",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: str = Header(None)) -> None:
    """Verify API key if LOTGENIUS_API_KEY is set."""
    required_key = os.getenv("LOTGENIUS_API_KEY")
    if required_key:
        if not x_api_key or x_api_key != required_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/v1/report", response_model=ReportResponse)
async def create_report(
    request: ReportRequest, _: None = Depends(verify_api_key)
) -> ReportResponse:
    """Generate a lot analysis report."""
    try:
        return generate_report(request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/v1/report/stream")
async def create_report_stream(
    request: ReportRequest, _: None = Depends(verify_api_key)
):
    """Generate a lot analysis report with streaming progress."""
    try:

        def event_generator() -> Generator[str, None, None]:
            for event in report_stream(request):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8787)
