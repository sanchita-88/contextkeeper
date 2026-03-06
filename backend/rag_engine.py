from pathlib import Path
from typing import List, Optional
import asyncio
from datetime import datetime

from vector_store import index_chunks, search, delete_project_vectors, count_project_vectors
from code_analyzer import walk_project, chunk_code, get_language_for_file
from graph_engine import get_context_for_query
from ai_service import answer_codebase_question, generate_mermaid_diagram
from database import AsyncSessionLocal, IndexedProjectDB
from sqlalchemy import select

# Track indexing progress in-memory
_indexing_progress: dict = {}

async def index_project(project_path: str, extensions: List[str] = None) -> dict:
    """
    Full indexing pipeline:
    1. Walk project files
    2. Parse + chunk each file
    3. Embed + store in Qdrant
    4. Update SQLite metadata
    """
    _indexing_progress[project_path] = {"status": "running", "progress": 0.0, "message": "Starting..."}
    
    try:
        files = walk_project(project_path, extensions)
        if not files:
            _indexing_progress[project_path] = {
                "status": "error", "progress": 0.0, "message": "No source files found"
            }
            return {"success": False, "message": "No source files found"}
        
        all_chunks = []
        total_files = len(files)
        
        for i, filepath in enumerate(files):
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
                chunks = chunk_code(filepath, content)
                all_chunks.extend(chunks)
            except OSError:
                continue
            
            progress = (i + 1) / total_files * 0.7  # Parsing = 70% of work
            _indexing_progress[project_path] = {
                "status": "running",
                "progress": progress,
                "message": f"Parsing files... ({i+1}/{total_files})"
            }
        
        # Index all chunks into Qdrant
        _indexing_progress[project_path]["message"] = "Uploading to vector database..."
        _indexing_progress[project_path]["progress"] = 0.75
        
        await index_chunks(all_chunks, project_path)
        
        # Save metadata to SQLite
        chunk_count = await count_project_vectors(project_path)
        async with AsyncSessionLocal() as db:
            existing = await db.get(IndexedProjectDB, project_path)
            if existing:
                existing.last_indexed = datetime.utcnow()
                existing.file_count = len(files)
                existing.chunk_count = chunk_count
            else:
                db.add(IndexedProjectDB(
                    project_path=project_path,
                    last_indexed=datetime.utcnow(),
                    file_count=len(files),
                    chunk_count=chunk_count,
                ))
            await db.commit()
        
        _indexing_progress[project_path] = {
            "status": "complete",
            "progress": 1.0,
            "message": f"Indexed {len(files)} files, {chunk_count} code chunks"
        }
        
        return {"success": True, "file_count": len(files), "chunk_count": chunk_count}
    
    except Exception as e:
        _indexing_progress[project_path] = {
            "status": "error", "progress": 0.0, "message": str(e)
        }
        return {"success": False, "message": str(e)}

async def get_indexing_status(project_path: str) -> dict:
    """Get current indexing status for a project."""
    if project_path in _indexing_progress:
        progress_data = _indexing_progress[project_path]
        return {
            "project_path": project_path,
            "indexed": progress_data["status"] == "complete",
            "progress": progress_data["progress"],
            "status_message": progress_data["message"],
            "file_count": 0,
            "chunk_count": 0,
            "last_indexed": None,
        }
    
    async with AsyncSessionLocal() as db:
        result = await db.get(IndexedProjectDB, project_path)
        if result:
            chunk_count = await count_project_vectors(project_path)
            return {
                "project_path": project_path,
                "indexed": True,
                "progress": 1.0,
                "status_message": f"Indexed {result.file_count} files",
                "file_count": result.file_count,
                "chunk_count": chunk_count,
                "last_indexed": result.last_indexed.isoformat() if result.last_indexed else None,
            }
    
    return {
        "project_path": project_path,
        "indexed": False,
        "progress": 0.0,
        "status_message": "Not indexed yet",
        "file_count": 0,
        "chunk_count": 0,
        "last_indexed": None,
    }

async def query(question: str, project_path: str, current_file: Optional[str] = None) -> dict:
    """
    Full RAG query pipeline:
    1. Embed question, search Qdrant
    2. Get graph context for top results
    3. Ask Groq with full context
    4. Optionally generate Mermaid diagram
    """
    # Check if project is indexed
    status = await get_indexing_status(project_path)
    if not status["indexed"]:
        return {
            "answer": "This project hasn't been indexed yet. Please click 'Index Project' in the sidebar first.",
            "relevant_files": [],
            "code_snippets": [],
            "mermaid_diagram": None,
            "confidence": 0.0,
        }
    
    # Search Qdrant for relevant chunks
    hits = await search(question, project_path, limit=10)
    
    if not hits:
        return {
            "answer": "No relevant code found for this question. Make sure the project is indexed.",
            "relevant_files": [],
            "code_snippets": [],
            "mermaid_diagram": None,
            "confidence": 0.0,
        }
    
    # Get unique files from results
    relevant_files = list(dict.fromkeys([h["file_path"] for h in hits]))
    
    # Get graph context
    graph_context = get_context_for_query(question)
    
    # Build code context for LLM
    code_chunks = [
        f"// {h['file_path']} (lines {h['start_line']}-{h['end_line']})\n{h['text']}"
        for h in hits[:8]
    ]
    
    # Get answer from Groq
    ai_result = await answer_codebase_question(question, code_chunks, graph_context)
    
    # Generate diagram if appropriate
    mermaid_diagram = None
    if ai_result.get("should_generate_diagram"):
        try:
            diagram_context = "\n\n".join(code_chunks[:4])
            mermaid_diagram = await generate_mermaid_diagram(
                question,
                diagram_context,
                ai_result.get("diagram_type", "sequence")
            )
        except Exception:
            mermaid_diagram = None
    
    # Build snippet objects
    snippets = []
    for hit in hits[:5]:
        snippets.append({
            "file_path": hit["file_path"],
            "start_line": hit["start_line"],
            "end_line": hit["end_line"],
            "content": hit["text"][:300],
            "relevance_score": hit["score"],
        })
    
    avg_score = sum(h["score"] for h in hits[:5]) / min(5, len(hits)) if hits else 0
    
    return {
        "answer": ai_result["answer"],
        "relevant_files": relevant_files[:8],
        "code_snippets": snippets,
        "mermaid_diagram": mermaid_diagram,
        "confidence": round(avg_score, 3),
    }
