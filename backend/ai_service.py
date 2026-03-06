from groq import AsyncGroq
from config import settings
import json
import re
from typing import List

# Single shared async client instance
_groq_client = AsyncGroq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are a Senior Software Engineer with 15+ years of experience specializing in codebase navigation, architecture analysis, and developer productivity. You help developers understand complex codebases, resume work after interruptions, and manage their focus time effectively. Always be concise, practical, and technically precise."""

# ------------------------------------------------------------------ #
# Module-level compiled regex constants reused by generate_mermaid_diagram
# and its sanitizer helpers.  Compiled once at import time, not per call.
# ------------------------------------------------------------------ #

# Matches the opening line of any supported Mermaid diagram type.
_DIAGRAM_HEADERS = re.compile(
    r'^(sequenceDiagram|flowchart\s+(?:TD|LR|RL|BT|TB)|classDiagram|graph\s+(?:TD|LR|RL|BT|TB))',
    re.IGNORECASE | re.MULTILINE,
)

# Mermaid keywords that can appear as the first token on a line with no
# special characters (e.g. "participant User", "end", "loop").
_MERMAID_KEYWORDS = re.compile(
    r'^(?:'
    r'sequenceDiagram|flowchart|classDiagram|graph'
    r'|participant\s|actor\s'
    r'|activate\s|deactivate\s'
    r'|loop\b|alt\b|else\b|end\b|opt\b|par\b|and\b|critical\b|break\b'
    r'|note\s|links?\s'
    r'|class\s|classDef\s|style\s|click\s'
    r'|subgraph\b|direction\s'
    r'|title\s|accTitle\s|accDescr\s'
    r')',
    re.IGNORECASE,
)

# Unambiguous arrow / edge operators.
_MERMAID_EDGE = re.compile(
    r'(?:-->|->|->>|-->>|\.\.>|==|~~|<\|--|--\|>)',
)

# Node declarations and class-member definitions.
# RHS of typed members is restricted to type-like tokens to prevent prose
# such as "Service returns" from matching.
_MERMAID_NODE = re.compile(
    r'(?:'
    r'\w+\s*[\[({].*[\])}]'                          # node with label:  A[Label] / A(Label) / A{Label}
    r'|\+?\w+\(.*\)\s*\w*'                           # class method:     +login(user) bool
    r'|\w+\s+(?:[A-Z]\w*|int|str|bool|float|void'   # typed member — RHS must look like a type
    r'|String|Int|Bool|Number|Float|Object|List'
    r'|Dict|Set|Any|None|Optional)\s*$'
    r')',
)

async def _call_groq(messages: list, model: str = None, max_tokens: int = 1024) -> str:
    """Core Groq API call. Returns content string."""
    chosen_model = model or settings.groq_smart_model
    response = await _groq_client.chat.completions.create(
        model=chosen_model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content

async def generate_context_summary(snapshot_data: dict) -> str:
    """Given open files, edits, TODOs — produce 2-3 sentence natural language summary."""
    open_files = [f["path"].split("/")[-1] for f in snapshot_data.get("open_files", [])]
    active_file = snapshot_data.get("active_file", "").split("/")[-1]
    todos = snapshot_data.get("todos", [])
    recent_edits = snapshot_data.get("recent_edits", [])

    prompt = f"""Describe in 2-3 concise sentences what this developer was working on.
Active file: {active_file}
Open files: {', '.join(open_files[:5])}
Recent edits: {json.dumps(recent_edits[:3])}
TODOs in code: {json.dumps(todos[:5])}

Write like: "You were [action] in [file], specifically [detail]. You had just [last action]."
Be specific with file names and line numbers if available."""

    return await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=256
    )

async def generate_next_steps(snapshot_data: dict) -> List[str]:
    """Return 3 most logical next steps as a JSON array of strings."""
    prompt = f"""Based on this developer's work state, what are the 3 most logical next steps?
Context: {json.dumps(snapshot_data, default=str)[:1500]}

Respond with ONLY a valid JSON array of 3 strings. Example:
["Add unit test for validateToken() at line 160", "Fix the signature algorithm mismatch bug on line 234", "Update the API documentation for the auth endpoint"]

Return ONLY the JSON array, nothing else."""

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=256
    )
    try:
        # Strip markdown code fences if present
        clean = re.sub(r'```(?:json)?|```', '', response).strip()
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        # Extract list items as fallback
        lines = [l.strip().strip('"').strip("'").strip("-").strip() 
                 for l in response.split('\n') if l.strip() and not l.strip().startswith('[')]
        return [l for l in lines if len(l) > 5][:3] or ["Review recent changes", "Run tests", "Update documentation"]

async def answer_codebase_question(question: str, code_chunks: List[str], graph_context: str) -> dict:
    """Answer a natural language question about the codebase using retrieved context."""
    context_text = "\n\n---\n\n".join(code_chunks[:8])
    
    prompt = f"""A developer asks: "{question}"

Here is the relevant code from the codebase:
{context_text[:6000]}

Graph relationships:
{graph_context[:1000]}

Provide a comprehensive answer that:
1. Directly answers the question
2. References specific files and line numbers
3. Explains the flow/architecture clearly
4. Mentions any edge cases or important considerations

Also indicate if a visual diagram would help (yes/no) and if yes, what type: sequence/flowchart/class."""

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        max_tokens=2048
    )
    
    should_diagram = any(kw in question.lower() for kw in 
                         ["flow", "process", "sequence", "how does", "what happens", "steps"])
    
    return {
        "answer": response,
        "should_generate_diagram": should_diagram,
        "diagram_type": "sequence" if "flow" in question.lower() else "flowchart"
    }

async def generate_mermaid_diagram(question: str, code_context: str, diagram_type: str = "sequence") -> str:
    """Generate valid Mermaid.js diagram syntax. Returns ONLY mermaid code."""

    # Fallback diagrams matched to the requested type so a sequence failure
    # doesn't silently return a flowchart to the user.
    _FALLBACKS = {
        "sequence": (
            "sequenceDiagram\n"
            "    participant Client\n"
            "    participant Server\n"
            "    Client->>Server: request\n"
            "    Server-->>Client: response"
        ),
        "class": (
            "classDiagram\n"
            "    class Service {\n"
            "        +handle(request) Response\n"
            "    }\n"
            "    class Repository {\n"
            "        +find(id) Object\n"
            "    }\n"
            "    Service --> Repository"
        ),
        "flowchart": (
            "flowchart TD\n"
            "    A[Request] --> B[Process]\n"
            "    B --> C[Service]\n"
            "    C --> D[Response]"
        ),
    }
    _FALLBACK = _FALLBACKS.get(diagram_type, _FALLBACKS["flowchart"])

    type_instructions = {
        "sequence": "sequenceDiagram with ->> and -->> message arrows",
        "flowchart": "flowchart TD with --> arrows",
        "class": "classDiagram with classes and relationships"
    }

    instruction = type_instructions.get(diagram_type, type_instructions["sequence"])

    prompt = f"""Generate a Mermaid.js {diagram_type} diagram for: "{question}"

Code context:
{code_context[:3000]}

Rules:
- Output must contain ONLY Mermaid code. If any explanation is added the answer is invalid.
- Do NOT add any text before or after the diagram. No preamble, no summary, no closing remarks.
- Use {instruction}
- Maximum 8 components
- Use CamelCase identifiers (no spaces)
- Node IDs must contain only letters and numbers. 
- Labels must be inside brackets.

Start diagrams exactly like:
sequenceDiagram
flowchart TD
classDiagram

Flowchart syntax:
A --> B
A -->|label| B

Sequence syntax:
User->>API: request
API-->>User: response
"""

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_smart_model,
        max_tokens=1024
    )

    # Debug: log raw LLM output so failures can be triaged at the right layer
    # (Groq generation vs sanitizer vs frontend Mermaid renderer).
    print("RAW MERMAID OUTPUT:\n", response)

    # ------------------------------------------------------------------ #
    # Step 1: Strip markdown fences                                        #
    # ------------------------------------------------------------------ #
    clean = re.sub(r'```(?:mermaid)?', '', response)
    clean = re.sub(r'```', '', clean).strip()

    # ------------------------------------------------------------------ #
    # Step 2: Normalise exotic Unicode arrows to ASCII equivalents         #
    # ------------------------------------------------------------------ #
    arrow_map = {
        "→":  "-->",
        "⇒":  "->>",
        "—>": "-->",
        "—>>": "->>",
        "–>":  "-->",
        "⟶":  "-->",
    }
    for bad, good in arrow_map.items():
        clean = clean.replace(bad, good)

    # ------------------------------------------------------------------ #
    # Step 3: Find the first valid diagram header and discard anything     #
    #         that appears before it (preamble / explanation text)         #
    # ------------------------------------------------------------------ #
    header_match = _DIAGRAM_HEADERS.search(clean)
    if not header_match:
        return _FALLBACK
    clean = clean[header_match.start():]

    # ------------------------------------------------------------------ #
    # Step 4: Discard any explanation text that appears AFTER the diagram  #
    #         block.  We keep only lines that look like Mermaid syntax.    #
    # ------------------------------------------------------------------ #
    def _is_diagram_line(line: str) -> bool:
        """
        Return True if the line is recognisable Mermaid content.

        Precedence (first match wins):
          1. Blank / whitespace-only  → keep (preserves indentation structure)
          2. Matches a Mermaid keyword prefix → keep
          3. Contains an arrow / edge operator → keep
          4. Matches a node / member definition pattern → keep
          5. Anything else → treat as prose; caller will stop accumulating
        """
        stripped = line.strip()
        if not stripped:
            return True
        if _MERMAID_KEYWORDS.match(stripped):
            return True
        if _MERMAID_EDGE.search(stripped):
            return True
        if _MERMAID_NODE.search(stripped):
            return True
        return False

    lines = clean.splitlines()
    trimmed_lines: list[str] = []
    for line in lines:
        if _is_diagram_line(line):
            trimmed_lines.append(line)
        else:
            # Stop at first clearly-prose line that follows diagram content
            if len(trimmed_lines) > 1:
                break
    clean = "\n".join(trimmed_lines).rstrip()

    # ------------------------------------------------------------------ #
    # Step 5: Diagram-type–specific cleanup                               #
    # Dispatch on the *actual* header found in the LLM output, not the   #
    # caller-supplied diagram_type — the LLM may ignore the requested     #
    # type and generate a different diagram kind entirely.  Running e.g.  #
    # _sanitize_flowchart on a sequenceDiagram would corrupt it.          #
    # ------------------------------------------------------------------ #
    if clean.startswith("sequenceDiagram"):
        clean = _sanitize_sequence(clean)
    elif clean.startswith(("flowchart", "graph")):
        clean = _sanitize_flowchart(clean)
    elif clean.startswith("classDiagram"):
        clean = _sanitize_class(clean)

    # ------------------------------------------------------------------ #
    # Step 6: Final validation – must still start with a known header     #
    # ------------------------------------------------------------------ #
    _VALID_STARTS = ("sequenceDiagram", "flowchart", "classDiagram", "graph ")
    if not any(clean.startswith(v) for v in _VALID_STARTS):
        return _FALLBACK

    return clean


# ------------------------------------------------------------------ #
# Helpers: per-type sanitisers                                         #
# ------------------------------------------------------------------ #

def _collect_flowchart_nodes(diagram: str) -> list[str]:
    """
    Return a deduplicated list of node IDs found in a flowchart diagram.

    Handles both forms:
      - Edge lines:   ``A --> B``  or  ``A -->|label| B``
      - Standalone declarations:  ``PaymentService[Payment Service]``
    """
    ids: list[str] = []

    # IDs that appear on the left side of an edge
    ids += re.findall(r'^\s*(\w+)\s*(?:-->|-\.->|==>)', diagram, flags=re.MULTILINE)
    # IDs that appear on the right side of an edge (after optional label)
    ids += re.findall(r'(?:-->|-\.->|==>)\s*(?:\|[^|]*\|\s*)?(\w+)', diagram)
    # Standalone node declarations:  NodeID[...] / NodeID(...) / NodeID{...}
    ids += re.findall(r'^\s*(\w+)\s*[\[({]', diagram, flags=re.MULTILINE)

    # Deduplicate while preserving order; exclude the header keyword itself
    seen: set[str] = set()
    result: list[str] = []
    for nid in ids:
        lower = nid.lower()
        if lower in ("flowchart", "td", "lr", "rl", "bt", "tb", "graph"):
            continue
        if nid not in seen:
            seen.add(nid)
            result.append(nid)
    return result


def _sanitize_flowchart(clean: str) -> str:
    """Apply flowchart-specific fixes."""
    _FALLBACK = "flowchart TD\n    A[Request] --> B[Process]\n    B --> C[Service]\n    C --> D[Response]"

    # Fix malformed label arrows: `|> label` → `| label`
    clean = re.sub(r'\|\>\s*', '| ', clean)
    # Ensure no space between `-->` and opening `|`
    clean = re.sub(r'-->\s+\|', '-->|', clean)

    # Convert `A --> B: label` → `A -->|label| B`
    clean = re.sub(
        r'(\w+)\s*-->\s*(\w+)\s*:\s*(.+)',
        lambda m: f"{m.group(1)} -->|{m.group(3).strip()}| {m.group(2)}",
        clean,
    )

    # Sequence arrows are invalid in flowcharts – replace with plain arrows
    clean = clean.replace("->>", "-->").replace("-->>", "-->")

    # Enforce 8-node limit using the robust node collector
    if len(_collect_flowchart_nodes(clean)) > 8:
        return _FALLBACK

    return clean


def _sanitize_sequence(clean: str) -> str:
    """Apply sequence-diagram–specific fixes (do NOT touch ->> / -->>)."""
    # Remove any stray flowchart-only constructs (e.g. square-bracket node defs on their own line)
    # that sometimes bleed in from the LLM.
    lines = []
    for line in clean.splitlines():
        # Drop bare flowchart node declarations like `A[Something]` that have no arrow
        if re.match(r'^\s*\w+\[[^\]]+\]\s*$', line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _sanitize_class(clean: str) -> str:
    """
    Apply classDiagram-specific fixes.

    Problems addressed
    ------------------
    1. LLMs frequently emit flowchart edge syntax inside classDiagram blocks:
           Question -->|generates|> MermaidDiagram
       Mermaid's class parser does not understand ``-->|label|`` at all and
       crashes.  We convert these to the valid classDiagram form:
           Question --> MermaidDiagram : generates
       Then strip the label if it is unquoted (see point 3).

    2. The ``|>`` triangle artifact (visible in the failing screenshot) is an
       LLM hallucination — it appears when the model conflates the Mermaid
       flowchart label syntax ``-->|label|`` with an inheritance arrow ``--|>``.
       We strip it unconditionally.

    3. Bare unquoted trailing labels crash older Mermaid builds:
           ClassA --> ClassB : uses      ← strip the label
           ClassA --> ClassB : "uses"    ← keep (quoted form is safe)

    Relationships covered (all standard classDiagram arrows):
        <|--  --|>  <|..  ..|>  --  ..  *--  --*  o--  --o  <--  -->
    """

    # ------------------------------------------------------------------ #
    # Step 1: Convert flowchart labelled edges to classDiagram syntax      #
    #   A -->|label|> B   →   A --> B                                      #
    #   A -->|label|  B   →   A --> B                                      #
    # (label is dropped here; bare labels cause crashes — see step 3)      #
    # ------------------------------------------------------------------ #
    clean = re.sub(
        r'(\w+)\s*-->\s*\|([^|]*)\|\>?\s*(\w+)',
        r'\1 --> \3',
        clean,
    )

    # ------------------------------------------------------------------ #
    # Step 2: Strip any remaining stray |> or |label> fragments            #
    # ------------------------------------------------------------------ #
    clean = re.sub(r'\|[^|\n]*\|?\s*>', ' ', clean)

    # ------------------------------------------------------------------ #
    # Step 3: Strip bare (unquoted) trailing relationship labels           #
    #   ClassA --|> ClassB : uses   →   ClassA --|> ClassB                 #
    #   ClassA --|> ClassB : "uses" →   unchanged (quoted form is safe)    #
    # ------------------------------------------------------------------ #
    _REL = r'(?:<\|--|--\|>|<\|\.\.|\.\.\|>|<--|-->|\*--|--\*|o--|--o|--|\.\.)'
    clean = re.sub(
        rf'(\w+\s*{_REL}\s*\w+)\s*:\s*(?!")([^\n"]+)',
        r'\1',
        clean,
    )

    return clean


async def classify_interruption(message: str, source: str, current_context: str) -> dict:
    """Classify an interruption request and generate auto-reply."""
    prompt = f"""Classify this interruption for a developer currently in deep work.

Interruption message: "{message}"
Source: {source}
Developer's current work: {current_context[:300]}

Classification rules:
- CRITICAL: Production down, security breach, data loss, system outage
- IMPORTANT: Code review needed today, blocker for another team, urgent bug (not production)
- DEFERRABLE: General questions, non-urgent reviews, information requests, meeting scheduling

Respond with ONLY a valid JSON object:
{{
  "priority": "critical|important|deferrable",
  "reason": "One sentence explaining why",
  "auto_reply": "A professional 2-3 sentence reply to buy focus time (if deferrable/important). Empty string if critical.",
  "defer_duration_minutes": 90,
  "action_required": "What the developer should actually do"
}}"""

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=512
    )
    
    try:
        clean = re.sub(r'```(?:json)?|```', '', response).strip()
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        return {
            "priority": "deferrable",
            "reason": "Could not classify, defaulting to deferrable",
            "auto_reply": f"Thanks for reaching out! I'm in a deep work session right now. I'll get back to you in about 90 minutes.",
            "defer_duration_minutes": 90,
            "action_required": "Review when focus block ends"
        }

async def generate_resume_briefing(snapshot: dict, time_away_minutes: int) -> str:
    """Generate a re-orientation message for a developer returning to work."""
    hours = time_away_minutes // 60
    mins = time_away_minutes % 60
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"
    
    prompt = f"""A developer is returning to work after {time_str} away. 
Give them a warm, concise re-orientation (3-4 sentences max).

Their saved context:
- Summary: {snapshot.get('ai_summary', 'Unknown task')}
- Active file: {snapshot.get('active_file', '').split('/')[-1]}
- Next steps: {json.dumps(snapshot.get('next_steps', []))}
- Open files: {[f['path'].split('/')[-1] for f in snapshot.get('open_files', [])[:3]]}

Format: "Welcome back! It's been [time]. [What they were doing]. Your next step is [first next step]."
Be specific and encouraging."""

    return await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=256
    )