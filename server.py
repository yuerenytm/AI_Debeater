"""FastAPI 后端 — SSE 流式辩论 API。"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from debate_core import MODEL_OPTIONS, run_debate_stream

app = FastAPI(title="AI辩论器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent / "frontend"


class DebateRequest(BaseModel):
    topic: str
    pro_model: str
    con_model: str


@app.get("/api/models")
def list_models():
    return {"models": list(MODEL_OPTIONS.keys())}


@app.get("/api/debate/stream")
def debate_stream(
    topic: str = Query(..., min_length=1),
    pro_model: str = Query(...),
    con_model: str = Query(...),
):
    if pro_model not in MODEL_OPTIONS:
        raise HTTPException(400, f"未知正方模型: {pro_model}")
    if con_model not in MODEL_OPTIONS:
        raise HTTPException(400, f"未知反方模型: {con_model}")

    def event_generator():
        try:
            for event in run_debate_stream(topic.strip(), pro_model, con_model):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
