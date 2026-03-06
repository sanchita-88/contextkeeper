from urllib import request

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List
import json
import uuid

from config import settings
from models import (
    ContextSnapshot, SnapshotCreateRequest,
    CodebaseQuery, CodebaseQueryResponse, CodeSnippet,
    IndexRequest, IndexStatus,
    InterruptionRequest, InterruptionResponse,
    DiagramRequest, ImpactAnalysis,
)
from database import init_db, get_db, SnapshotDB, IndexedProjectDB, InterruptionLogDB
import ai_service
import vector_store
import code_analyzer
import graph_engine
import rag_engine
import context_manager
import interruption_service
import diagram_service


# ─── Startup & Shutdown ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await vector_store.ensure_collection()
    yield


# ─── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ContextKeeper API",
    description="Developer Intelligence Hub — AI-powered context saving and codebase comprehension",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "timestamp": datetime.utcnow().isoformat()}


# ─── Snapshots ─────────────────────────────────────────────────────────────

@app.post("/snapshots", response_model=ContextSnapshot)
async def create_snapshot(
    request: SnapshotCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new context snapshot with AI-generated summary and next steps."""
    snapshot_data = request.model_dump()

    # Generate AI content in parallel-ish via sequential awaits
    ai_summary = await ai_service.generate_context_summary(snapshot_data)
    next_steps = await ai_service.generate_next_steps(snapshot_data)

    snapshot = ContextSnapshot(
        **snapshot_data,
        ai_summary=ai_summary,
        next_steps=next_steps,
    )

    # Persist to SQLite
    db_record = SnapshotDB(
        id=snapshot.id,
        name=snapshot.name,
        project_path=snapshot.project_path,
        timestamp=snapshot.timestamp,
        data_json=snapshot.model_dump_json(),
    )
    db.add(db_record)
    await db.commit()

    return snapshot


@app.get("/snapshots", response_model=List[ContextSnapshot])
async def list_snapshots(db: AsyncSession = Depends(get_db)):
    """List all context snapshots ordered by most recent."""
    result = await db.execute(
        select(SnapshotDB).order_by(SnapshotDB.timestamp.desc()).limit(50)
    )
    rows = result.scalars().all()
    snapshots = []
    for row in rows:
        try:
            snapshots.append(ContextSnapshot(**json.loads(row.data_json)))
        except Exception:
            pass
    return snapshots


@app.get("/snapshots/{snapshot_id}", response_model=ContextSnapshot)
async def get_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a single snapshot by ID."""
    result = await db.execute(
        select(SnapshotDB).where(SnapshotDB.id == snapshot_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return ContextSnapshot(**json.loads(row.data_json))


@app.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a snapshot by ID."""
    result = await db.execute(
        select(SnapshotDB).where(SnapshotDB.id == snapshot_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    await db.delete(row)
    await db.commit()
    return {"deleted": True}


# ─── Resume / Re-orientation ───────────────────────────────────────────────

@app.get("/snapshots/{snapshot_id}/resume")
async def resume_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    """Get a snapshot plus an AI-generated re-orientation briefing."""
    result = await db.execute(
        select(SnapshotDB).where(SnapshotDB.id == snapshot_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    snapshot = ContextSnapshot(**json.loads(row.data_json))
    time_away = int((datetime.utcnow() - snapshot.timestamp).total_seconds() / 60)
    briefing = await ai_service.generate_resume_briefing(
        snapshot.model_dump(mode="json"), time_away
    )
    return {"snapshot": snapshot, "briefing": briefing}


# ─── Codebase Indexing ──────────────────────────────────────────────────────

# In-memory indexing progress tracker (use Redis in production)
_indexing_progress: dict = {}


@app.post("/index")
async def index_project(request: IndexRequest, background_tasks: BackgroundTasks):
    """Start background indexing of a project directory."""
    job_id = str(uuid.uuid4())
    _indexing_progress[request.project_path] = {
        "job_id": job_id,
        "progress": 0.0,
        "status": "starting",
        "file_count": 0,
        "chunk_count": 0,
    }
    background_tasks.add_task(
        _run_indexing, request.project_path, request.file_extensions
    )
    return {"job_id": job_id, "status": "started"}


async def _run_indexing(project_path: str, extensions: List[str]):
    """Background task: walk directory, parse files, embed chunks."""
    from pathlib import Path
    import asyncio

    progress = _indexing_progress.setdefault(project_path, {})
    progress["status"] = "scanning"

    files = code_analyzer.scan_project(project_path, extensions)
    total = len(files)
    progress["file_count"] = total
    progress["status"] = "indexing"

    all_chunks = []
    for i, filepath in enumerate(files):
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
            chunks = code_analyzer.chunk_code(filepath, content)
            # Add graph edges
            parsed = code_analyzer.parse_file(filepath, content)
            graph_engine.add_file(filepath, parsed)
            all_chunks.extend(chunks)
        except Exception:
            pass
        progress["progress"] = (i + 1) / total * 0.8

    # Batch embed and store
    await vector_store.index_chunks(all_chunks, project_path)
    progress["chunk_count"] = len(all_chunks)
    progress["progress"] = 1.0
    progress["status"] = "done"


@app.get("/index/status", response_model=IndexStatus)
async def get_index_status(project_path: str):
    """Get current indexing status for a project."""
    prog = _indexing_progress.get(project_path)
    if not prog:
        return IndexStatus(project_path=project_path, indexed=False, status_message="Not indexed")
    return IndexStatus(
        project_path=project_path,
        indexed=prog["status"] == "done",
        file_count=prog.get("file_count", 0),
        chunk_count=prog.get("chunk_count", 0),
        progress=prog.get("progress", 0.0),
        status_message=prog.get("status", ""),
    )


# ─── Codebase Q&A ──────────────────────────────────────────────────────────

@app.post("/query", response_model=CodebaseQueryResponse)
async def query_codebase(request: CodebaseQuery):
    """RAG-powered natural language question answering over indexed codebase."""

    progress = _indexing_progress.get(request.project_path)

    # Check if indexing finished
    if not progress or progress.get("status") != "done":
        return CodebaseQueryResponse(
            answer="This project hasn't finished indexing yet. Please wait for indexing to complete.",
            relevant_files=[],
            code_snippets=[],
            mermaid_diagram=None,
            confidence=0.0,
        )

    # Run vector search
    hits = await vector_store.search(request.question, request.project_path, limit=8)

    if not hits:
        return CodebaseQueryResponse(
            answer="No relevant code found for this question.",
            relevant_files=[],
            code_snippets=[],
            mermaid_diagram=None,
            confidence=0.0,
        )

    # Build code chunks and graph context
    code_chunks = [h["text"] for h in hits]
    graph_context = graph_engine.get_context_for_query(request.question)

    # Generate AI answer
    ai_result = await ai_service.answer_codebase_question(
        request.question, code_chunks, graph_context
    )

    mermaid_diagram = None
    if ai_result.get("should_generate_diagram"):
        context_str = "\n\n".join(code_chunks[:4])
        mermaid_diagram = await ai_service.generate_mermaid_diagram(
            request.question,
            context_str,
            ai_result.get("diagram_type", "sequence"),
        )

    snippets = [
        CodeSnippet(
            file_path=h["file_path"],
            start_line=h["start_line"],
            end_line=h["end_line"],
            content=h["text"][:500],
            relevance_score=h["score"],
        )
        for h in hits[:5]
    ]

    relevant_files = list(dict.fromkeys(h["file_path"] for h in hits))

    return CodebaseQueryResponse(
        answer=ai_result["answer"],
        relevant_files=relevant_files,
        code_snippets=snippets,
        mermaid_diagram=mermaid_diagram,
        confidence=hits[0]["score"] if hits else 0.0,
    )


# ─── Diagrams ──────────────────────────────────────────────────────────────

@app.post("/diagram")
async def generate_diagram(request: DiagramRequest):
    """Generate a Mermaid.js diagram for a natural language query."""
    # Safely attempt RAG search — project may not be indexed yet
    code_context = ""
    try:
        hits = await vector_store.search(request.query, request.project_path, limit=5)
        if hits:
            code_context = "\n\n".join(h["text"] for h in hits)
    except Exception:
        # Qdrant collection may not exist yet — generate diagram without code context
        code_context = ""

    # Always generate a diagram, with or without code context
    mermaid = await ai_service.generate_mermaid_diagram(
        request.query, code_context, request.diagram_type
    )
    return {"mermaid": mermaid, "type": request.diagram_type}


# ─── Impact Analysis ────────────────────────────────────────────────────────

@app.get("/impact")
async def impact_analysis(function_name: str, project_path: str):
    """Analyze what breaks if a function is changed."""
    affected = graph_engine.get_impact(function_name)
    return ImpactAnalysis(
        function_name=function_name,
        affected_functions=affected.get("functions", []),
        affected_files=affected.get("files", []),
        risk_level=affected.get("risk_level", "low"),
        explanation=affected.get("explanation", ""),
    )


# ─── Interruptions ─────────────────────────────────────────────────────────

@app.post("/interruptions/classify", response_model=InterruptionResponse)
async def classify_interruption(
    request: InterruptionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Classify an interruption and generate a professional auto-reply."""
    result = await ai_service.classify_interruption(
        request.message, request.source, request.current_context
    )

    # Log to DB
    log = InterruptionLogDB(
        message=request.message,
        source=request.source,
        priority=result.get("priority", "deferrable"),
        auto_reply=result.get("auto_reply", ""),
    )
    db.add(log)
    await db.commit()

    return InterruptionResponse(
        priority=result.get("priority", "deferrable"),
        reason=result.get("reason", ""),
        auto_reply=result.get("auto_reply", ""),
        defer_duration_minutes=int(result.get("defer_duration_minutes", 90)),
        action_required=result.get("action_required", ""),
    )


@app.get("/interruptions")
async def list_interruptions(db: AsyncSession = Depends(get_db)):
    """List all past interruptions."""
    result = await db.execute(
        select(InterruptionLogDB).order_by(InterruptionLogDB.timestamp.desc()).limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "source": r.source,
            "message": r.message,
            "priority": r.priority,
            "auto_reply": r.auto_reply,
        }
        for r in rows
    ]


# ─── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.backend_port, reload=True)
