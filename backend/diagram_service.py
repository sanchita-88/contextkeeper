from ai_service import generate_mermaid_diagram
from rag_engine import query as rag_query
from typing import Optional

async def generate_flow_diagram(diagram_query: str, project_path: str, diagram_type: str = "sequence") -> str:
    """Generate a Mermaid diagram for a flow/architecture question."""
    # Get relevant code from RAG
    rag_result = await rag_query(diagram_query, project_path)
    
    if not rag_result.get("relevant_files"):
        # Generate without code context
        return await generate_mermaid_diagram(diagram_query, "", diagram_type)
    
    code_context = "\n\n".join(
        f"// {s['file_path']}\n{s['content']}"
        for s in rag_result.get("code_snippets", [])[:4]
    )
    
    return await generate_mermaid_diagram(diagram_query, code_context, diagram_type)
