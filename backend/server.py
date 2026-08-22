"""FastAPI server for Guardian Call M0.

Provides HTTP endpoints to process conversational text, execute the canonical
Guardian Call M0 pipeline, and stream real backend domain events via SSE.
"""

import asyncio
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# Ensure repository root directory and backend directory are on sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.guardian.events import EventType, GuardianEvent, InMemoryEventSink
from backend.guardian.extractor import (
    DEFAULT_GEMINI_MODEL,
    ExtractionError,
    GeminiSignalExtractor,
    SignalExtractor,
)
from backend.guardian.pipeline import GuardianPipeline, PipelineResult


class LazyGeminiExtractor:
    """Extractor wrapper that instantiates GeminiSignalExtractor dynamically or raises ExtractionError."""

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model

    def extract_signals(self, text: str):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ExtractionError(
                "No Gemini API key provided. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.",
                error_type="API_KEY_MISSING",
            )
        extractor = GeminiSignalExtractor(api_key=api_key, model=self.model)
        return extractor.extract_signals(text)


app = FastAPI(
    title="Guardian Call — Backend Event API",
    description="Agentic phone-scam protection system powered by Gemini and Canary Policy Engine",
    version="1.0.0",
)

# Enable CORS for local development and browser visualizer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE event broadcast subscribers
event_subscribers: List[asyncio.Queue] = []


async def broadcast_event(event_data: Dict[str, Any]) -> None:
    """Broadcast a real domain event payload to all connected SSE clients."""
    for queue in list(event_subscribers):
        try:
            await queue.put(event_data)
        except Exception:
            pass


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Conversational text snippet to analyze")


class AnalyzeResponse(BaseModel):
    signals: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    canary_decision: Optional[Dict[str, Any]] = None
    warning: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


@app.get("/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    """Return service health status and configuration info."""
    api_key_set = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return {
        "status": "healthy",
        "service": "guardian-call-backend",
        "model": os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        "has_api_key": api_key_set,
    }


@app.get("/api/v1/scenarios", tags=["Scenarios"])
def list_scenarios() -> Dict[str, Any]:
    """List available synthetic demo scenarios from the scenarios directory."""
    scenarios_path = root_dir / "scenarios"
    scenarios: List[Dict[str, Any]] = []

    if scenarios_path.exists():
        for file_path in sorted(scenarios_path.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scenarios.append({
                        "id": data.get("scenario_id", file_path.stem),
                        "title": data.get("title", file_path.stem),
                        "description": data.get("description", ""),
                        "dialogue": data.get("dialogue", []),
                        "expected_final_risk": data.get("expected_final_risk", "NORMAL"),
                        "expected_warning_directive": data.get("expected_warning_directive"),
                    })
            except Exception:
                continue

    return {"status": "success", "count": len(scenarios), "scenarios": scenarios}


@app.post(
    "/api/v1/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
)
async def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze conversational text input through Gemini signal extraction and Guardian M0 pipeline.

    Broadcasts all emitted canonical domain events to connected SSE visualizers.
    """
    sink = InMemoryEventSink()
    pipeline = GuardianPipeline(extractor=LazyGeminiExtractor())

    result: PipelineResult = pipeline.process_text(request.text, event_sink=sink)

    # Broadcast every canonical domain event emitted by the pipeline execution to active SSE clients
    for event in result.events:
        await broadcast_event(event.to_dict())

    return AnalyzeResponse(
        signals=result.signals.to_dict() if result.signals else None,
        risk_assessment=result.risk_assessment.to_dict() if result.risk_assessment else None,
        canary_decision=result.canary_decision.to_dict() if result.canary_decision else None,
        warning=result.warning_event.to_dict() if result.warning_event else None,
        events=[e.to_dict() for e in result.events],
        error=str(result.error) if result.error else None,
    )


@app.get("/api/v1/events/stream", tags=["Realtime Telemetry"])
async def stream_events():
    """Server-Sent Events (SSE) endpoint for real-time visualizer streaming of domain events."""
    queue: asyncio.Queue = asyncio.Queue()
    event_subscribers.append(queue)

    async def event_generator():
        try:
            # Yield initial connection confirmation event
            init_event = {
                "event_type": "STREAM_CONNECTED",
                "payload": {"status": "connected"},
            }
            yield f"data: {json.dumps(init_event)}\n\n"

            while True:
                event_data = await queue.get()
                yield f"data: {json.dumps(event_data)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in event_subscribers:
                event_subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Mount frontend visualizer static files
frontend_dir = root_dir / "frontend" / "visualizer"
if frontend_dir.exists():
    app.mount("/visualizer", StaticFiles(directory=str(frontend_dir), html=True), name="visualizer")

    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/visualizer/")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
