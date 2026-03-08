"""
groq_service.py — ContextKeeper AI backend
============================================
Handles all LLM interactions via Groq: codebase Q&A, context summarisation,
Mermaid diagram generation + sanitisation, interruption classification, and
resume briefing generation.

Public API (all async):
    _call_groq
    generate_context_summary
    generate_next_steps
    answer_codebase_question
    generate_mermaid_diagram
    classify_interruption
    generate_resume_briefing
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import List

from groq import AsyncGroq

from config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client (single shared instance)
# ---------------------------------------------------------------------------

_groq_client = AsyncGroq(api_key=settings.groq_api_key)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a Senior Software Engineer with 15+ years of experience in "
    "codebase navigation, architecture analysis, and developer productivity. "
    "Your primary goal is to extract REAL structure from provided source code. "
    "Rules:\n"
    "  • Never hallucinate classes, components, or relationships not present in the code.\n"
    "  • When generating diagrams, use ONLY identifiers that exist in the code context.\n"
    "  • Prefer concise, accurate answers over exhaustive ones.\n"
    "  • Reference specific file paths and line numbers when available.\n"
    "  • When asked for JSON, return ONLY valid JSON — no preamble, no code fences."
)

# ---------------------------------------------------------------------------
# Deterministic fallback diagrams
# ---------------------------------------------------------------------------

_FALLBACKS: dict[str, str] = {
    "sequence": (
        "sequenceDiagram\n"
        "    participant Client\n"
        "    participant Server\n"
        "    Client->>Server: request\n"
        "    Server-->>Client: response"
    ),
    "class": (
        "classDiagram\n"
        "    class A\n"
        "    class B\n"
        "    A --|> B"
    ),
    "flowchart": (
        "flowchart TD\n"
        "    A[Request] --> B[Process]\n"
        "    B --> C[Service]\n"
        "    C --> D[Response]"
    ),
}


def _build_fallback(diagram_type: str, allowlist: list[str]) -> str:
    names = allowlist[:_MAX_NODES] if allowlist else []

    if diagram_type == "class" and names:
        lines = ["classDiagram"]
        for name in names:
            lines.append(f"    class {name}")
        return "\n".join(lines)

    if diagram_type == "flowchart" and names:
        decls = "\n".join(f"    {name}[{name}]" for name in names[:4])
        return f"flowchart TD\n{decls}"

    return _FALLBACKS.get(diagram_type, _FALLBACKS["flowchart"])

# ---------------------------------------------------------------------------
# Module-level compiled regexes
# ---------------------------------------------------------------------------

_RE_DIAGRAM_HEADER = re.compile(
    r"^(sequenceDiagram|flowchart\s+(?:TD|LR|RL|BT|TB)"
    r"|classDiagram|graph\s+(?:TD|LR|RL|BT|TB))",
    re.IGNORECASE | re.MULTILINE,
)

# FIX 1: participant\b and actor\b instead of participant\s / actor\s
# so "participant User as User" is not stripped by _remove_prose_lines
_RE_MERMAID_KW = re.compile(
    r"^(?:"
    r"sequenceDiagram|flowchart|classDiagram|graph"
    r"|participant\b|actor\b"
    r"|activate\s|deactivate\s"
    r"|loop\b|alt\b|else\b|end\b|opt\b|par\b|and\b|critical\b|break\b"
    r"|note\s|links?\s"
    r"|class\s|classDef\s|style\s|click\s"
    r"|subgraph\b|direction\s"
    r"|title\s|accTitle\s|accDescr\s"
    r")",
    re.IGNORECASE,
)

# FIX 2: expanded to include class-diagram arrow operators ..> --* *-- o-- --o
_RE_MERMAID_EDGE = re.compile(
    r"(?:-->|->>|-->>|--\|>|<\|--|\.\.>|--\*|\*--|o--|--o)"
)

_RE_MERMAID_NODE = re.compile(
    r"(?:"
    r"[A-Za-z][A-Za-z0-9_]*\s*[\[({].*[\])}]"
    r"|\+?[A-Za-z]\w*\(.*\)\s*\w*"
    r"|[A-Za-z]\w*\s+(?:[A-Z]\w*|int|str|bool|float|void"
    r"|String|Int|Bool|Number|Float|Object|List"
    r"|Dict|Set|Any|None|Optional)\s*$"
    r")"
)

_RE_CLASS_DECL = re.compile(
    r"(?:export\s+|public\s+|private\s+|protected\s+)?"
    r"(?:abstract\s+|data\s+|sealed\s+|open\s+)?"
    r"(?:class|interface)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

_UNICODE_ARROW_MAP: dict[str, str] = {
    "→":   "-->",
    "⇒":   "->>",
    "—>":  "-->",
    "—>>": "->>",
    "–>":  "-->",
    "⟶":  "-->",
}

_VALID_STARTS = ("sequenceDiagram", "flowchart", "classDiagram", "graph ")

_MAX_NODES = 10

# ---------------------------------------------------------------------------
# Retryable exception set
# ---------------------------------------------------------------------------

_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    TimeoutError, ConnectionError, OSError, RuntimeError
)
try:
    import groq as _groq_pkg
    _RETRYABLE_EXCEPTIONS += tuple(
        cls
        for name in ("APIStatusError", "APIConnectionError", "RateLimitError")
        if (cls := getattr(_groq_pkg, name, None)) is not None
    )
except Exception:
    pass

# ---------------------------------------------------------------------------
# Core Groq helper
# ---------------------------------------------------------------------------


async def _call_groq(
    messages: list,
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    chosen_model = model or settings.groq_smart_model
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for attempt in range(2):
        try:
            response = await _groq_client.chat.completions.create(
                model=chosen_model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except _RETRYABLE_EXCEPTIONS as exc:
            if attempt == 0:
                logger.warning(
                    "Groq API call failed (attempt 1/2): %s — retrying in 0.5s…", exc
                )
                await asyncio.sleep(0.5)
            else:
                logger.error("Groq API call failed (attempt 2/2): %s — giving up.", exc)
                raise
        except Exception:
            raise


# ---------------------------------------------------------------------------
# Class / node allowlist extraction
# ---------------------------------------------------------------------------


def _extract_class_names(code_context: str, max_names: int = _MAX_NODES) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for match in _RE_CLASS_DECL.finditer(code_context):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            names.append(name)
            if len(names) >= max_names:
                break
    return names


# ---------------------------------------------------------------------------
# Diagram sanitisation pipeline
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r"```(?:mermaid)?", "", text)
    return re.sub(r"```", "", text).strip()


def _normalise_unicode_arrows(text: str) -> str:
    for bad, good in _UNICODE_ARROW_MAP.items():
        text = text.replace(bad, good)
    return text


_PREFERRED_PATTERNS: dict[str, re.Pattern[str]] = {
    "sequence":  re.compile(r"sequenceDiagram", re.IGNORECASE),
    "flowchart": re.compile(r"(?:flowchart\s+(?:TD|LR|RL|BT|TB)|graph\s+(?:TD|LR|RL|BT|TB))", re.IGNORECASE),
    "class":     re.compile(r"classDiagram", re.IGNORECASE),
}


def _has_body(block: str) -> bool:
    return any(
        ln.strip() and not _RE_DIAGRAM_HEADER.match(ln.strip())
        for ln in block.splitlines()
    )


def _infer_type(block: str) -> str:
    stripped = block.lstrip()
    if stripped.startswith("sequenceDiagram"):
        return "sequence"
    if stripped.startswith(("flowchart", "graph")):
        return "flowchart"
    if stripped.startswith("classDiagram"):
        return "class"
    return "unknown"


def _extract_best_block(text: str, requested: str) -> str | None:
    header_matches = list(_RE_DIAGRAM_HEADER.finditer(text))
    if not header_matches:
        return None

    logger.debug(
        "_extract_best_block: found %d header(s) at positions %s",
        len(header_matches),
        [(m.group(0).strip(), m.start()) for m in header_matches],
    )

    candidates: list[str] = []
    for i, m in enumerate(header_matches):
        start = m.start()
        end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(text)
        candidates.append(text[start:end])

    preferred_re = _PREFERRED_PATTERNS.get(requested)
    pref: list[str] = []
    rest: list[str] = []
    for c in candidates:
        (pref if preferred_re and preferred_re.match(c.lstrip()) else rest).append(c)

    search_order = list(reversed(pref)) + list(reversed(rest))

    best_wrong_type: tuple[str, str] | None = None

    for idx, raw_cand in enumerate(search_order):
        cand = _strip_markdown_fences(raw_cand)
        cand = _normalise_unicode_arrows(cand)
        cand = _remove_prose_lines(cand)

        if not _has_body(cand):
            logger.debug("_extract_best_block: candidate %d is header-only, skipping.", idx)
            continue

        inferred = _infer_type(cand)

        if inferred == requested:
            logger.debug("_extract_best_block: candidate %d accepted (type=%r).", idx, inferred)
            return cand

        if inferred != "unknown" and best_wrong_type is None:
            best_wrong_type = (cand, inferred)
            logger.debug(
                "_extract_best_block: candidate %d type %r ≠ requested %r — keeping as downgrade.",
                idx, inferred, requested,
            )

    if best_wrong_type is not None:
        cand, inferred = best_wrong_type
        logger.warning(
            "_extract_best_block: no %r block found; downgrading to %r.",
            requested, inferred,
        )
        return cand

    logger.warning(
        "_extract_best_block: no valid block found (requested=%r).", requested
    )
    return None


def _remove_prose_lines(text: str) -> str:
    def _is_diagram_line(line: str, inside_block: bool) -> bool:
        stripped = line.strip()
        if not stripped:
            return True
        if _RE_MERMAID_KW.match(stripped):
            return True
        if _RE_MERMAID_EDGE.search(stripped):
            return True
        if (
            inside_block
            and _RE_MERMAID_NODE.search(stripped)
            and any(ch in stripped for ch in "([{")
        ):
            return True
        return False

    trimmed: list[str] = []
    brace_depth = 0
    for line in text.splitlines():
        opens = line.count("{")
        closes = line.count("}")
        was_open = brace_depth > 0
        brace_depth = max(brace_depth + opens - closes, 0)

        inside = len(trimmed) > 1

        if was_open or brace_depth > 0:
            trimmed.append(line)
        elif _is_diagram_line(line, inside_block=inside):
            trimmed.append(line)
        elif len(trimmed) > 1:
            break
    return "\n".join(trimmed).rstrip()


def _enforce_node_allowlist(diagram: str, allowlist: list[str]) -> str:
    if not allowlist:
        return diagram

    allowed_names = set(allowlist)
    _RE_NODE_LABEL = re.compile(r"\b(\w+)\[([^\]]+)\]")
    effective_allowed: set[str] = set(allowed_names)
    for m in _RE_NODE_LABEL.finditer(diagram):
        node_id, label = m.group(1), m.group(2).strip()
        if label in allowed_names:
            effective_allowed.add(node_id)

    _RE_ARROW_IDS = re.compile(
        r"([A-Za-z][A-Za-z0-9_]*)\s*"
        r"(?:-->|->>|-->>|--\|>|<\|--)"
        r"(?:\s*\|[^|]*\|\s*)?"
        r"\s*([A-Za-z][A-Za-z0-9_]*)"
    )

    output: list[str] = []
    for line in diagram.splitlines():
        stripped = line.strip()
        if not stripped or _RE_DIAGRAM_HEADER.match(stripped):
            output.append(line)
            continue
        endpoint_ids = []
        for m in _RE_ARROW_IDS.finditer(stripped):
            endpoint_ids.extend([m.group(1), m.group(2)])
        if not endpoint_ids:
            output.append(line)
            continue
        if all(tok in effective_allowed for tok in endpoint_ids):
            output.append(line)
        else:
            foreign = [t for t in endpoint_ids if t not in effective_allowed]
            logger.debug("Allowlist: dropping line with foreign nodes %s: %r", foreign, stripped)

    return "\n".join(output)


def _count_nodes(diagram: str) -> int:
    ids: set[str] = set()

    for match in re.finditer(
        r"^\s*(\w+)\s*(?:-->|->>|-->>|--\|>|<\|--)", diagram, re.MULTILINE
    ):
        ids.add(match.group(1))
    for match in re.finditer(
        r"(?:-->|->>|-->>|--\|>|<\|--)\s*(?:\|[^|]*\|\s*)?(\w+)", diagram
    ):
        ids.add(match.group(1))
    for match in re.finditer(r"^\s*(\w+)\s*[\[({]", diagram, re.MULTILINE):
        ids.add(match.group(1))
    for match in re.finditer(r"^\s*class\s+(\w+)\s*(?:\{|$)", diagram, re.MULTILINE):
        ids.add(match.group(1))
    for match in re.finditer(r"^\s*participant\s+(\w+)", diagram, re.MULTILINE):
        ids.add(match.group(1))

    _META = {
        "flowchart", "sequenceDiagram", "classDiagram", "graph",
        "TD", "LR", "RL", "BT", "TB",
    }
    ids -= _META
    return len(ids)


# ---------------------------------------------------------------------------
# Diagram-type-specific fixes
# ---------------------------------------------------------------------------


def _fix_flowchart(diagram: str) -> str:
    diagram = re.sub(r"\b(\w+)\[\1\]", r"\1", diagram)
    diagram = re.sub(r"\|\>\s*", "| ", diagram)
    diagram = re.sub(r"-->\s+\|", "-->|", diagram)
    diagram = re.sub(
        r"(\w+)\s*-->\s*(\w+)\s*:\s*([^|][^\n]*)",
        lambda m: f"{m.group(1)} -->|{m.group(3).strip()}| {m.group(2)}",
        diagram,
    )
    diagram = diagram.replace("->>", "-->").replace("-->>", "-->")
    # Strip trailing whitespace — some Mermaid versions reject lines ending in spaces
    diagram = "\n".join(ln.rstrip() for ln in diagram.splitlines())
    return diagram


def _fix_sequence(diagram: str) -> str:
    lines: list[str] = []
    for line in diagram.splitlines():
        if re.match(r"^\s*\w+\[[^\]]+\]\s*$", line):
            continue
        # FIX: strip quoted participant aliases: participant X as "Y" → participant X as Y
        line = re.sub(r'(participant\s+\w+(?:\s+as\s+)?)"([^"]+)"', r'\1\2', line)
        lines.append(line.rstrip())

    if not any(re.match(r"^\s*participant\s+", ln) for ln in lines):
        seen: set[str] = set()
        ordered: list[str] = []
        for ln in lines:
            m = re.match(r"^\s*(\w+)\s*(?:-->>|->>|-->|->)\s*(\w+)\s*:", ln)
            if m:
                for name in (m.group(1), m.group(2)):
                    if name not in seen:
                        seen.add(name)
                        ordered.append(name)
        if ordered:
            injected: list[str] = []
            inserted = False
            for ln in lines:
                injected.append(ln)
                if not inserted and ln.strip().lower() == "sequencediagram":
                    for name in ordered:
                        injected.append(f"    participant {name}")
                    inserted = True
            lines = injected

    return "\n".join(lines)


def _fix_class(diagram: str) -> str:
    """
    Apply classDiagram-specific corrections.

    Step 0: Strip ALL [Label] syntax first (source nodes, standalone decls).
    Step 1: Convert flowchart pipe-label edges  A -->|label| B → A --> B : label
    Step 2: Convert bracket target labels       A --> B[label] → A --> B : label
    Step 3: Strip any residual [Label] occurrences
    Step 4: Strip stray |…|> fragments
    Step 5: Wrap bare ``class Name`` lines in braces
    """
    fixed_lines: list[str] = []
    in_class_body = False

    for line in diagram.splitlines():
        stripped = line.strip()

        opens  = stripped.count("{")
        closes = stripped.count("}")
        was_in_body = in_class_body
        in_class_body = max(int(in_class_body) + opens - closes, 0) > 0

        if was_in_body:
            fixed_lines.append(line)
            continue

        # ── Step 0: strip ALL [Label] syntax immediately ──────────────────────
        # Must be first so "RechargeDAO [RechargeDAO] --> PlanDAO [PlanDAO]"
        # becomes "RechargeDAO --> PlanDAO" before any other rule runs.
        line = re.sub(r"\b(\w+)\s*\[[^\]]+\]", r"\1", line)

        # ── Step 1: flowchart pipe-label edges ────────────────────────────────
        line = re.sub(
            r"(\w+)\s*-->\s*\|([^|]+)\|\s*(\w+)",
            r"\1 --> \3 : \2",
            line,
        )

        # ── Step 2: bracket target labels on relationship lines ───────────────
        _CLASS_ARROWS = r"(?:-->|\.\.>|--\|>|\|>--|<\|--|--\*|\*--|o--|--o|\.\.)"
        line = re.sub(
            rf"({_CLASS_ARROWS}\s*)(\w+)\s*\[([^\]]+)\]",
            lambda m: (
                f"{m.group(1)}{m.group(2)} : {m.group(3)}"
                if m.group(2) != m.group(3)
                else f"{m.group(1)}{m.group(2)}"
            ),
            line,
        )

        # ── Step 3: strip any residual [Label] occurrences ───────────────────
        line = re.sub(r"\b(\w+)\s*\[[^\]]+\]", r"\1", line)

        # ── Step 4: strip stray |…|> fragments ───────────────────────────────
        line = re.sub(r"\|[^|\n]*\|?\s*>", " ", line)

        # ── Step 5: wrap bare ``class Name`` declarations in braces ──────────
        if re.match(r"^\s*class\s+\w+\s*$", line):
            fixed_lines.append(line.rstrip() + " {")
            fixed_lines.append("}")
            continue

        if line.strip():
            fixed_lines.append(line)

    diagram = "\n".join(fixed_lines)

    if not diagram.strip().startswith("classDiagram"):
        return "classDiagram\n"

    missing = diagram.count("{") - diagram.count("}")
    if missing > 0:
        diagram = diagram.rstrip() + "\n}" * missing

    logger.debug("_fix_class output:\n%s", diagram)
    return diagram.strip()


# ---------------------------------------------------------------------------
# Unified sanitisation pipeline
# ---------------------------------------------------------------------------


def _sanitise_diagram(
    raw: str,
    diagram_type: str,
    allowlist: list[str],
) -> str:
    fallback = _build_fallback(diagram_type, allowlist)

    logger.debug("_sanitise_diagram: raw LLM output:\n%s", raw)

    # ── Fast path ─────────────────────────────────────────────────────────────
    # FIX 5: never fast-path class diagrams with [Label] syntax or sequence
    # diagrams with quoted aliases — both need their fixers to run.
    _fast_candidate = raw.strip()
    if (
        any(_fast_candidate.startswith(v) for v in _VALID_STARTS)
        and _infer_type(_fast_candidate) == diagram_type
        and _has_body(_fast_candidate)
        and not (diagram_type == "class" and re.search(r"\b\w+\s*\[", _fast_candidate))
        and not (diagram_type == "sequence" and re.search(r'participant\s+\w+.*as\s+"', _fast_candidate))
        and (
            diagram_type == "sequence"
            or _count_nodes(_fast_candidate) <= _MAX_NODES
        )
    ):
        logger.debug("_sanitise_diagram: fast-path accepted (no mutation needed).")
        return _fast_candidate

    pre = _strip_markdown_fences(raw)
    pre = _normalise_unicode_arrows(pre)

    clean = _extract_best_block(pre, requested=diagram_type)
    if clean is None:
        logger.warning("_sanitise_diagram: no valid %r block found; using fallback.", diagram_type)
        return fallback

    actual_type = _infer_type(clean)
    if actual_type == "sequence":
        clean = _fix_sequence(clean)
    elif actual_type == "flowchart":
        clean = _fix_flowchart(clean)
    elif actual_type == "class":
        clean = _fix_class(clean)

    if actual_type != diagram_type:
        logger.warning(
            "_sanitise_diagram: requested %r, rendering %r (graceful downgrade).",
            diagram_type, actual_type,
        )

    # FIX 4: allowlist enforcement disabled for flowcharts.
    # Single-letter node IDs (A, B, C) generated by the LLM never match
    # class-name allowlists, causing every edge to be stripped.
    if False and allowlist and actual_type == "flowchart":  # noqa: SIM210
        clean = _enforce_node_allowlist(clean, allowlist)
        if _count_nodes(clean) == 0:
            logger.warning(
                "Allowlist filtering removed all nodes from flowchart; using fallback."
            )
            return fallback

    if actual_type != "sequence":
        node_count = _count_nodes(clean)
        if node_count > _MAX_NODES:
            logger.warning(
                "Diagram has %d nodes (ceiling %d, type=%r); using fallback.",
                node_count, _MAX_NODES, actual_type,
            )
            return fallback

    if not any(clean.startswith(v) for v in _VALID_STARTS):
        logger.warning("Diagram has no valid header after fixes; using fallback.")
        return fallback

    if not _has_body(clean):
        logger.warning("Diagram is header-only after fixes; using fallback.")
        return fallback

    logger.debug("_sanitise_diagram: final output:\n%s", clean)
    return clean


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------


async def generate_context_summary(snapshot_data: dict) -> str:
    open_files = [f["path"].split("/")[-1] for f in snapshot_data.get("open_files", [])]
    active_file = snapshot_data.get("active_file", "").split("/")[-1]
    todos = snapshot_data.get("todos", [])
    recent_edits = snapshot_data.get("recent_edits", [])

    prompt = (
        f"Describe in 2-3 concise sentences what this developer was working on.\n"
        f"Active file: {active_file}\n"
        f"Open files: {', '.join(open_files[:5])}\n"
        f"Recent edits: {json.dumps(recent_edits[:3])}\n"
        f"TODOs in code: {json.dumps(todos[:5])}\n\n"
        f'Write like: "You were [action] in [file], specifically [detail]. '
        f'You had just [last action]."\n'
        f"Be specific with file names and line numbers if available."
    )

    return await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=256,
    )


async def generate_next_steps(snapshot_data: dict) -> List[str]:
    prompt = (
        f"Based on this developer's work state, what are the 3 most logical next steps?\n"
        f"Context: {json.dumps(snapshot_data, default=str)[:1500]}\n\n"
        f"Respond with ONLY a valid JSON array of 3 strings. Example:\n"
        f'["Add unit test for validateToken() at line 160", '
        f'"Fix the signature algorithm mismatch bug on line 234", '
        f'"Update the API documentation for the auth endpoint"]\n\n'
        f"Return ONLY the JSON array, nothing else."
    )

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=256,
    )

    try:
        clean = re.sub(r"```(?:json)?|```", "", response).strip()
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        logger.warning("generate_next_steps: JSON parse failed; extracting lines.")
        lines = [
            ln.strip().strip('"').strip("'").strip("-").strip()
            for ln in response.split("\n")
            if ln.strip() and not ln.strip().startswith("[")
        ]
        candidates = [ln for ln in lines if len(ln) > 5][:3]
        return candidates or ["Review recent changes", "Run tests", "Update documentation"]


async def answer_codebase_question(
    question: str,
    code_chunks: List[str],
    graph_context: str,
) -> dict:
    context_text = "\n\n---\n\n".join(code_chunks[:8])

    prompt = (
        f'A developer asks: "{question}"\n\n'
        f"Relevant code from the codebase:\n{context_text[:6000]}\n\n"
        f"Graph relationships:\n{graph_context[:1000]}\n\n"
        f"Provide a comprehensive answer that:\n"
        f"1. Directly answers the question.\n"
        f"2. References specific files and line numbers.\n"
        f"3. Explains the flow/architecture clearly.\n"
        f"4. Mentions any edge cases or important considerations.\n\n"
        f"Also indicate if a visual diagram would help (yes/no) and if yes, "
        f"what type: sequence / flowchart / class."
    )

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        max_tokens=2048,
    )

    should_diagram = any(
        kw in question.lower()
        for kw in ["flow", "process", "sequence", "how does", "what happens", "steps"]
    )

    return {
        "answer": response,
        "should_generate_diagram": should_diagram,
        "diagram_type": "sequence" if "flow" in question.lower() else "flowchart",
    }


def _extract_structural_lines(code_context: str, char_limit: int = 3000) -> str:
    if len(code_context) <= char_limit:
        return code_context

    lines = code_context.splitlines()

    _RE_CLASS_LINE = re.compile(
        r"^\s*(?:export\s+|public\s+|private\s+|protected\s+)?"
        r"(?:abstract\s+|data\s+|sealed\s+|open\s+)?"
        r"(?:class|interface)\s+\w",
        re.IGNORECASE,
    )
    _RE_IMPORT_LINE = re.compile(
        r"^\s*(?:from\s+\S+\s+import|import\s+\S+|require\s*\(|using\s+\S+|#include\s+)",
    )
    _RE_FUNC_LINE = re.compile(
        r"^\s*(?:"
        r"(?:async\s+)?def\s+"
        r"|(?:export\s+)?(?:async\s+)?function\s+"
        r"|(?:public|private|protected|static|override|open)\s+(?:fun|func|void|int|str|bool|auto|var)\s+"
        r"|(?:async\s+)?func\s+"
        r"|fun\s+"
        r")",
        re.IGNORECASE,
    )

    seen: set[str] = set()
    buckets: list[list[str]] = [[], [], [], []]

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)

        if _RE_CLASS_LINE.match(line):
            buckets[0].append(line)
        elif _RE_IMPORT_LINE.match(line):
            buckets[1].append(line)
        elif _RE_FUNC_LINE.match(line):
            buckets[2].append(line)
        else:
            buckets[3].append(line)

    result_lines: list[str] = []
    chars = 0
    for bucket in buckets:
        for line in bucket:
            cost = len(line) + 1
            if chars + cost > char_limit:
                break
            result_lines.append(line)
            chars += cost

    extracted = "\n".join(result_lines)
    logger.debug(
        "_extract_structural_lines: %d → %d chars (%d lines extracted from %d)",
        len(code_context), len(extracted), len(result_lines), len(lines),
    )
    return extracted


async def generate_mermaid_diagram(
    question: str,
    code_context: str,
    diagram_type: str = "sequence",
) -> str:
    fallback = _build_fallback(diagram_type, [])

    allowlist = _extract_class_names(code_context)
    logger.debug("generate_mermaid_diagram: allowlist=%s", allowlist)

    if len(question.split()) <= 4:
        question = (
            f"Generate a {diagram_type} diagram of the core classes and "
            f"relationships found in this codebase."
        )

    type_instructions = {
        "sequence": "sequenceDiagram with ->> and -->> message arrows",
        "flowchart": "flowchart TD with --> arrows",
        "class": "classDiagram with classes and relationships",
    }
    instruction = type_instructions.get(diagram_type, type_instructions["sequence"])

    _RE_IMPORT = re.compile(
        r"^\s*(?:"
        r"from\s+\S+\s+import"
        r"|import\s+\S+"
        r"|require\s*\("
        r"|using\s+\S+"
        r"|#include\s+"
        r")"
    )
    _STDLIB_NOISE = re.compile(
        r"(?:^|[\s'\"])(?:"
        r"typing|os|sys|re|json|math|io|abc|collections|functools|"
        r"itertools|pathlib|logging|datetime|time|copy|enum|dataclasses|"
        r"string|struct|types|weakref|contextlib|inspect|traceback|warnings"
        r")(?:\.|['\"\s]|$)"
    )
    import_lines = [
        ln.strip()
        for ln in code_context.splitlines()
        if _RE_IMPORT.match(ln) and not _STDLIB_NOISE.search(ln)
    ][:20]
    imports_section = (
        "Module / dependency imports extracted from the codebase:\n"
        + "\n".join(f"  {ln}" for ln in import_lines)
        + "\n\n"
        if import_lines
        else ""
    )

    if diagram_type == "sequence":
        allowlist_section = (
            "For sequence diagrams, participants should be interaction roles "
            "derived from the code context (e.g., User, API, Controller, Service, "
            "Database). They do NOT need to match class names exactly.\n"
            + (
                f"Classes detected in this codebase for context: "
                f"{', '.join(allowlist)}\n"
                if allowlist
                else ""
            )
            + "\n"
        )
    elif allowlist:
        allowlist_section = (
            "Detected classes/components — USE ONLY THESE as node identifiers:\n"
            + "\n".join(f"  - {name}" for name in allowlist)
            + "\n\n"
        )
    else:
        allowlist_section = (
            "No class names were auto-detected. Infer components strictly from "
            "the code context below. Do NOT invent names absent from the code.\n\n"
        )

    code_snippet = _extract_structural_lines(code_context)

    _REQUIRED_HEADER: dict[str, str] = {
        "sequence":  "sequenceDiagram",
        "flowchart": "flowchart TD",
        "class":     "classDiagram",
    }
    required_header = _REQUIRED_HEADER.get(diagram_type, "flowchart TD")

    prompt = (
        f"Generate a Mermaid.js {diagram_type} diagram of the architecture "
        f"described by the code below.\n\n"
        f"STRICT RULES:\n"
        f"- Output ONLY Mermaid syntax — no explanation, no preamble, no remarks.\n"
        f"- You MUST generate a {diagram_type} diagram. DO NOT generate any other type.\n"
        f"- Your response MUST start EXACTLY with: {required_header}\n"
        f"- Use {instruction}.\n"
        f"- Maximum {_MAX_NODES} components"
        + (" (sequence diagrams may use more participants if needed).\n" if diagram_type == "sequence" else ".\n")
        + ("- Node IDs: letters and numbers only, CamelCase. Labels go inside brackets.\n\n"
           if diagram_type != "sequence"
           else "- Participant names should be short, role-based identifiers (e.g. User, API, AuthService).\n"
                "- Do NOT use quoted aliases like participant X as \"Y\". Use plain: participant X\n\n")
        + f"{allowlist_section}"
        f"{imports_section}"
        f"User request (hint — do NOT diagram this sentence):\n{question}\n\n"
        f"Code context (infer relationships from this):\n{code_snippet}\n\n"
        f"Begin your response with exactly this line and nothing before it:\n"
        f"{required_header}\n"
    )

    try:
        raw = await _call_groq(
            [{"role": "user", "content": prompt}],
            model=settings.groq_smart_model,
            max_tokens=1024,
        )
    except Exception:
        logger.error("generate_mermaid_diagram: LLM call failed; using fallback.")
        return _build_fallback(diagram_type, allowlist)

    logger.debug("generate_mermaid_diagram: raw LLM output:\n%s", raw)

    return _sanitise_diagram(raw, diagram_type, allowlist)


async def classify_interruption(
    message: str,
    source: str,
    current_context: str,
) -> dict:
    prompt = (
        f"Classify this interruption for a developer currently in deep work.\n\n"
        f'Interruption message: "{message}"\n'
        f"Source: {source}\n"
        f"Developer's current work: {current_context[:300]}\n\n"
        f"Classification rules:\n"
        f"- CRITICAL: Production down, security breach, data loss, system outage.\n"
        f"- IMPORTANT: Code review needed today, blocker for another team, urgent bug.\n"
        f"- DEFERRABLE: General questions, non-urgent reviews, information requests.\n\n"
        f"Respond with ONLY a valid JSON object:\n"
        f'{{\n'
        f'  "priority": "critical|important|deferrable",\n'
        f'  "reason": "One sentence explaining why",\n'
        f'  "auto_reply": "2-3 sentence professional reply (empty string if critical)",\n'
        f'  "defer_duration_minutes": 90,\n'
        f'  "action_required": "What the developer should actually do"\n'
        f"}}"
    )

    response = await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=512,
    )

    try:
        clean = re.sub(r"```(?:json)?|```", "", response).strip()
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        logger.warning("classify_interruption: JSON parse failed; using default.")
        return {
            "priority": "deferrable",
            "reason": "Could not classify, defaulting to deferrable.",
            "auto_reply": (
                "Thanks for reaching out! I'm in a deep work session right now. "
                "I'll get back to you in about 90 minutes."
            ),
            "defer_duration_minutes": 90,
            "action_required": "Review when focus block ends.",
        }


async def generate_resume_briefing(snapshot: dict, time_away_minutes: int) -> str:
    hours = time_away_minutes // 60
    mins = time_away_minutes % 60
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"

    open_filenames = [
        f["path"].split("/")[-1] for f in snapshot.get("open_files", [])[:3]
    ]

    prompt = (
        f"A developer is returning to work after {time_str} away.\n"
        f"Give them a warm, concise re-orientation (3-4 sentences max).\n\n"
        f"Their saved context:\n"
        f"- Summary: {snapshot.get('ai_summary', 'Unknown task')}\n"
        f"- Active file: {snapshot.get('active_file', '').split('/')[-1]}\n"
        f"- Next steps: {json.dumps(snapshot.get('next_steps', []))}\n"
        f"- Open files: {open_filenames}\n\n"
        f'Format: "Welcome back! It\'s been [time]. [What they were doing]. '
        f'Your next step is [first next step]."\n'
        f"Be specific and encouraging."
    )

    return await _call_groq(
        [{"role": "user", "content": prompt}],
        model=settings.groq_fast_model,
        max_tokens=256,
    )

# ---------------------------------------------------------------------------
# Sanitiser unit tests
# Run with:  python groq_service.py
# ---------------------------------------------------------------------------

def _run_sanitiser_tests() -> None:
    failures: list[str] = []

    def _assert(condition: bool, name: str, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))
        if not condition:
            failures.append(name)

    print("\n=== Sanitiser unit tests ===")

    # Test 1
    t1_input = (
        "classDiagram\n\n"
        "flowchart TD\n"
        "  A[Main] --> B[RequestHandler]\n"
        "  B[RequestHandler] --> C[Authentication]\n"
    )
    t1_result = _extract_best_block(t1_input, requested="flowchart")
    _assert(t1_result is not None and t1_result.lstrip().startswith("flowchart TD"),
            "Test 1: preamble classDiagram, real flowchart returned")
    _assert(t1_result is not None and "A[Main]" in t1_result,
            "Test 1: flowchart body content preserved")

    # Test 2
    t2_input = "flowchart TD\n\nflowchart TD\n  A --> B\n  B --> C\n"
    t2_result = _extract_best_block(t2_input, requested="flowchart")
    _assert(t2_result is not None and "A --> B" in t2_result,
            "Test 2: last valid flowchart block chosen")

    # Test 3
    t3_input = "classDiagram\n\nflowchart TD\n  A --> B\n"
    t3_result = _extract_best_block(t3_input, requested="flowchart")
    _assert(t3_result is not None and t3_result.lstrip().startswith("flowchart TD"),
            "Test 3: bare classDiagram skipped")

    # Test 4: class [Label] stripping
    t4_input = (
        "classDiagram\n"
        "    RechargeDAO [RechargeDAO] --> PlanDAO [PlanDAO]\n"
        "    GenerateHash [GenerateHash] ..> RechargeDAO [RechargeDAO]\n"
    )
    t4_result = _sanitise_diagram(t4_input, "class", [])
    _assert(t4_result is not None and "RechargeDAO --> PlanDAO" in t4_result,
            "Test 4: [Label] stripped from class edges")
    _assert(t4_result is not None and "GenerateHash ..> RechargeDAO" in t4_result,
            "Test 4: ..> edges preserved after strip")
    _assert(t4_result is not None and "[" not in t4_result.split("classDiagram")[1],
            "Test 4: no [ remains in class diagram body")

    # Test 5: sequence quoted aliases stripped
    t5_input = (
        'sequenceDiagram\n'
        '    participant User as "User"\n'
        '    participant RechargeDAO as "RechargeDAO"\n'
        '    User->>RechargeDAO: requestRecharge()\n'
        '    RechargeDAO-->>User: result()\n'
    )
    t5_result = _fix_sequence(t5_input)
    _assert('as "User"' not in t5_result, "Test 5: quoted alias stripped from sequence")
    _assert("User->>RechargeDAO" in t5_result, "Test 5: message arrows preserved")

    # Test 6: flowchart trailing whitespace
    t6_input = "flowchart TD\n    A --> B   \n    B --> C\t\n"
    t6_result = _fix_flowchart(t6_input)
    for ln in t6_result.splitlines():
        _assert(ln == ln.rstrip(), f"Test 6: no trailing whitespace on: {repr(ln)}")

    # Test 7: class body members preserved
    t7_input = (
        "classDiagram\n"
        "    class UserController {\n"
        "        +getUsers()\n"
        "        +getUser(id)\n"
        "    }\n"
        "    UserController --> UserService\n"
    )
    t7_result = _sanitise_diagram(t7_input, "class", [])
    _assert(t7_result is not None and "+getUsers()" in t7_result,
            "Test 7: class body members preserved")
    _assert(t7_result is not None and "UserController --> UserService" in t7_result,
            "Test 7: inter-class edge preserved")

    # Test 8: _MAX_NODES ceiling inclusive
    nodes = [chr(65 + i) for i in range(_MAX_NODES)]
    t8_lines = ["flowchart TD"] + [
        f"    {nodes[i]}[N{i}] --> {nodes[i+1]}[N{i+1}]" for i in range(_MAX_NODES - 1)
    ]
    t8_result = _sanitise_diagram("\n".join(t8_lines), "flowchart", [])
    _assert(t8_result is not None and _count_nodes(t8_result) == _MAX_NODES,
            f"Test 8: exactly {_MAX_NODES} nodes passes ceiling")

    print(f"\n  {len(failures)} failure(s)" if failures else "\n  All tests passed.")
    if failures:
        raise AssertionError(f"Sanitiser tests failed: {failures}")


if __name__ == "__main__":
    _run_sanitiser_tests()