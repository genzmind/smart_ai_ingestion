import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from smart_ingestion.agents.registry import agent_registry
from smart_ingestion.config import LLM_PROVIDER, UPLOADS_DIR
from smart_ingestion.models import AgentInfo, ChatRequest, ConfirmRequest, UploadResponse
from smart_ingestion.orchestrator import orchestrator

app = FastAPI(
    title="SMART AI Ingestion",
    description="Intelligent multi-source data ingestion orchestrator",
    version="1.1.0",
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    return cleaned or f"upload_{uuid.uuid4().hex[:8]}.csv"


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_provider": LLM_PROVIDER}


@app.get("/api/agents", response_model=list[AgentInfo])
def list_agents():
    return [agent.info() for agent in agent_registry.all()]


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    filename = _safe_filename(file.filename or "upload.csv")
    dest = UPLOADS_DIR / filename
    content = await file.read()
    dest.write_bytes(content)
    relative = f"uploads/{filename}"
    return UploadResponse(filename=filename, path=relative, size_bytes=len(content))


@app.post("/api/chat")
def chat(request: ChatRequest):
    return orchestrator.handle_message(request.session_id, request.message)


@app.post("/api/confirm")
def confirm(request: ConfirmRequest):
    return orchestrator.handle_confirm(request.session_id, request.confirmed)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
