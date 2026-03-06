try:
    from tree_sitter_language_pack import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    try:
        from tree_sitter_languages import get_language, get_parser
        TREE_SITTER_AVAILABLE = True
    except ImportError:
        TREE_SITTER_AVAILABLE = False

from pathlib import Path
from typing import List, Dict, Optional
import re

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
}

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "__pycache__",
    ".venv", "venv", "env", ".env", "coverage", ".nyc_output", "vendor"
}

def get_language_for_file(filepath: str) -> Optional[str]:
    ext = Path(filepath).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext)

def parse_file(filepath: str, content: str) -> Dict:
    """
    Parse a source file and extract functions, classes, and imports.
    Returns: {functions, classes, imports, language}
    """
    language_name = get_language_for_file(filepath)
    if not language_name or not TREE_SITTER_AVAILABLE:
        return {"functions": [], "classes": [], "imports": [], "language": "unknown"}
    
    try:
        language = get_language(language_name)
        parser = get_parser(language_name)
        tree = parser.parse(bytes(content, "utf-8"))
        root = tree.root_node
    except Exception:
        return {"functions": [], "classes": [], "imports": [], "language": language_name}
    
    functions = []
    classes = []
    imports = []
    
    def get_text(node) -> str:
        return content[node.start_byte:node.end_byte]
    
    def traverse(node, parent_class: str = ""):
        node_type = node.type
        
        # Python functions
        if node_type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = get_text(name_node)
                functions.append({
                    "name": func_name,
                    "full_name": f"{parent_class}.{func_name}" if parent_class else func_name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "parent_class": parent_class,
                })
        
        # TypeScript/JavaScript functions
        elif node_type in ("function_declaration", "method_definition", "arrow_function"):
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = get_text(name_node)
                functions.append({
                    "name": func_name,
                    "full_name": f"{parent_class}.{func_name}" if parent_class else func_name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "parent_class": parent_class,
                })
        
        # Classes (Python, TS, JS, Java)
        elif node_type in ("class_definition", "class_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = get_text(name_node)
                classes.append({
                    "name": class_name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                })
                # Recurse into class body with class context
                for child in node.children:
                    traverse(child, parent_class=class_name)
                return  # Don't double-traverse children
        
        # Import statements
        elif node_type in ("import_statement", "import_from_statement", "import_declaration"):
            imports.append(get_text(node).strip()[:200])
        
        for child in node.children:
            traverse(child, parent_class)
    
    traverse(root)
    
    return {
        "functions": functions,
        "classes": classes,
        "imports": imports[:50],
        "language": language_name,
    }

def chunk_code(filepath: str, content: str, max_chunk_lines: int = 60) -> List[Dict]:
    """
    Split code into semantic chunks for embedding.
    Tries to split by function/class boundaries first, then by line count.
    Returns list of {text, file_path, start_line, end_line, function_name, language}
    """
    language_name = get_language_for_file(filepath) or "unknown"
    parsed = parse_file(filepath, content)
    lines = content.split("\n")
    total_lines = len(lines)
    chunks = []
    
    # If we found functions, create chunks around them
    if parsed["functions"]:
        for func in parsed["functions"]:
            start = max(0, func["start_line"] - 1)
            end = min(total_lines, func["end_line"])
            chunk_lines = lines[start:end]
            chunk_text = "\n".join(chunk_lines)
            
            if len(chunk_text.strip()) > 20:  # Skip trivial chunks
                chunks.append({
                    "text": f"# File: {filepath}\n# Function: {func['full_name']}\n\n{chunk_text}",
                    "file_path": filepath,
                    "start_line": func["start_line"],
                    "end_line": func["end_line"],
                    "function_name": func["full_name"],
                    "language": language_name,
                })
    
    # Also add file-level chunk (imports + first 50 lines) for context
    if total_lines > 0:
        header_lines = min(50, total_lines)
        header_text = "\n".join(lines[:header_lines])
        chunks.append({
            "text": f"# File: {filepath} (header/imports)\n\n{header_text}",
            "file_path": filepath,
            "start_line": 1,
            "end_line": header_lines,
            "function_name": "__module__",
            "language": language_name,
        })
    
    # If no functions found, chunk by line count
    if not parsed["functions"] and total_lines > 0:
        for i in range(0, total_lines, max_chunk_lines):
            end = min(i + max_chunk_lines, total_lines)
            chunk_text = "\n".join(lines[i:end])
            if len(chunk_text.strip()) > 20:
                chunks.append({
                    "text": f"# File: {filepath} (lines {i+1}-{end})\n\n{chunk_text}",
                    "file_path": filepath,
                    "start_line": i + 1,
                    "end_line": end,
                    "function_name": "",
                    "language": language_name,
                })
    
    return chunks

def walk_project(project_path: str, extensions: List[str] = None) -> List[str]:
    """Walk a project directory and return all source file paths, skipping ignored dirs."""
    extensions = extensions or list(SUPPORTED_EXTENSIONS.keys())
    files = []
    
    for path in Path(project_path).rglob("*"):
        # Skip ignored directories
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in extensions:
            files.append(str(path))
    
    return sorted(files)

# Alias used by main.py
scan_project = walk_project
