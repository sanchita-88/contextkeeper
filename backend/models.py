from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class FileState(BaseModel):
    path: str
    cursor_line: int = 0
    cursor_col: int = 0
    scroll_top: int = 0
    is_dirty: bool = False

class EditRecord(BaseModel):
    file: str
    line: int
    timestamp: str

class ContextSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_path: str
    open_files: List[FileState] = []
    active_file: str = ""
    recent_edits: List[EditRecord] = []
    todos: List[str] = []
    terminal_commands: List[str] = []
    ai_summary: str = ""
    next_steps: List[str] = []
    tags: List[str] = []
    time_spent_minutes: int = 0

class SnapshotCreateRequest(BaseModel):
    name: str
    project_path: str
    open_files: List[FileState] = []
    active_file: str = ""
    recent_edits: List[EditRecord] = []
    todos: List[str] = []
    terminal_commands: List[str] = []
    tags: List[str] = []

class CodeSnippet(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    content: str
    relevance_score: float

class CodebaseQuery(BaseModel):
    question: str
    project_path: str
    current_file: Optional[str] = None

class CodebaseQueryResponse(BaseModel):
    answer: str
    relevant_files: List[str] = []
    code_snippets: List[CodeSnippet] = []
    mermaid_diagram: Optional[str] = None
    confidence: float = 0.0

class IndexRequest(BaseModel):
    project_path: str
    file_extensions: List[str] = [".ts", ".tsx", ".py", ".js", ".jsx", ".java", ".go"]

class IndexStatus(BaseModel):
    project_path: str
    indexed: bool
    file_count: int = 0
    chunk_count: int = 0
    last_indexed: Optional[str] = None
    progress: float = 0.0
    status_message: str = ""

class InterruptionRequest(BaseModel):
    message: str
    source: str  # "slack", "code_review", "production", "meeting", "other"
    current_context: str = ""

class InterruptionResponse(BaseModel):
    priority: str  # "critical", "important", "deferrable"
    reason: str
    auto_reply: str
    defer_duration_minutes: int
    action_required: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DiagramRequest(BaseModel):
    query: str
    project_path: str
    diagram_type: str = "sequence"  # "sequence", "flowchart", "class"

class ImpactAnalysis(BaseModel):
    function_name: str
    affected_functions: List[str] = []
    affected_files: List[str] = []
    risk_level: str = "low"
    explanation: str = ""
