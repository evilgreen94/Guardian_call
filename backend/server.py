"""Google Cloud Run compatible FastAPI server for Guardian Call M0.

Provides HTTP endpoints to process conversational text, execute the Google ADK
signal extraction pipeline, and stream real backend domain events.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend package directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from guardian.events import InMemoryEventSink
from guardian.pipeline import GuardianPipeline


app = FastAPI(
    title="Guardian Call — Backend Event API",
    description="Agentic phone-scam protection system powered by Google ADK and Gemini",
    version="0.5.0",
)

# Enable CORS for frontend visualizer integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend visualizer static files if directory exists
frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "visualizer"
if frontend_dir.exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/visualizer", StaticFiles(directory=str(frontend_dir), html=True), name="visualizer")

    @app.get("/", tags=["System"])
    def root() -> FileResponse:
        """Serve the Guardian Visualizer UI at root."""
        return FileResponse(str(frontend_dir / "index.html"))


class AnalyzeRequest(BaseModel):
    """Payload for text analysis request."""
    text: str = Field(
        ...,
        description="Conversational text segment to evaluate for scam indicators.",
        examples=["Tell me the six-digit code you just received from your bank."],
    )


class AnalyzeResponse(BaseModel):
    """Structured response containing risk state, Canary decision, and full event trail."""
    signals: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    canary_decision: Dict[str, Any]
    warning: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]]


@app.get("/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    """Health check endpoint for Google Cloud Run probes."""
    return {
        "status": "healthy",
        "service": "guardian-call-backend",
        "model": "gemini-3.5-flash",
        "framework": "google-adk",
        "use_vertex_ai": os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1"),
        "has_api_key": bool(os.getenv("GOOGLE_API_KEY")),
    }


@app.post(
    "/api/v1/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
)
def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze conversational text input through Google ADK and Canary policy engine."""
    sink = InMemoryEventSink()
    pipeline = GuardianPipeline()

    try:
        result = pipeline.process_text(request.text, event_sink=sink)
        return AnalyzeResponse(
            signals=result.signals.to_dict(),
            risk_assessment=result.risk_assessment.to_dict(),
            canary_decision=result.canary_decision.to_dict(),
            warning=result.warning_event.to_dict() if result.warning_event else None,
            events=[e.to_dict() for e in result.events],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing error: {str(exc)}",
        ) from exc


@app.post(
    "/api/v1/analyze-image",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
)
async def analyze_image(file: UploadFile = File(...)) -> AnalyzeResponse:
    """Analyze image/screenshot input through Google ADK vision agent and Guardian pipeline."""
    sink = InMemoryEventSink()
    pipeline = GuardianPipeline()

    try:
        content = await file.read()
        mime_type = file.content_type or "image/png"
        result = pipeline.process_image(content, mime_type=mime_type, event_sink=sink)
        return AnalyzeResponse(
            signals=result.signals.to_dict(),
            risk_assessment=result.risk_assessment.to_dict(),
            canary_decision=result.canary_decision.to_dict(),
            warning=result.warning_event.to_dict() if result.warning_event else None,
            events=[e.to_dict() for e in result.events],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image processing error: {str(exc)}",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
