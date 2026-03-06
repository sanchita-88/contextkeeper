import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select

from database import AsyncSessionLocal, SnapshotDB
from models import ContextSnapshot, SnapshotCreateRequest
from ai_service import generate_context_summary, generate_next_steps, generate_resume_briefing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_snapshot_name(snapshot: ContextSnapshot) -> str:
    """
    Generate a meaningful snapshot name when the caller did not supply one
    or supplied the Pydantic default placeholder "string".

    Priority:
      1. Use the active file's basename (e.g. "auth.service.ts")
      2. Use the first open file's basename
      3. Fall back to a generic timestamped label
    """
    active = snapshot.active_file or ""
    if active:
        basename = active.rstrip("/").split("/")[-1]
        if basename:
            return f"{basename} checkpoint"

    open_files = snapshot.open_files or []
    if open_files:
        first = open_files[0]
        path = getattr(first, "path", "") or ""
        basename = path.rstrip("/").split("/")[-1]
        if basename:
            return f"{basename} checkpoint"

    # Last resort: timestamp-based label
    ts = datetime.now(timezone.utc).strftime("%b %d %H:%M")
    return f"Saved Checkpoint — {ts}"


def _needs_generated_name(name: Optional[str]) -> bool:
    """Return True when the name is absent or a known placeholder."""
    if not name:
        return True
    stripped = name.strip().lower()
    # "string" is the default value Pydantic emits for str fields without a default
    return stripped in {"", "string", "unknown"}


def _ensure_ai_context(snapshot_dict: dict) -> dict:
    """
    Return a copy of snapshot_dict that is guaranteed to contain the fields
    the AI summary and next-steps functions depend on.  Missing or None values
    are replaced with safe, non-empty defaults so the LLM always receives
    meaningful context rather than empty strings.
    """
    enriched = dict(snapshot_dict)

    # active_file — derive from open_files if absent
    if not enriched.get("active_file"):
        open_files = enriched.get("open_files") or []
        if open_files:
            first = open_files[0]
            path = getattr(first, "path", "") or ""
            enriched["active_file"] = path or "unknown_file"
        else:
            enriched["active_file"] = "unknown_file"

    # open_files — must be a list
    if not enriched.get("open_files"):
        enriched["open_files"] = [{"path": enriched["active_file"], "cursor_line": 0}]

    # recent_edits — must be a list (empty is fine; the LLM handles it gracefully)
    if enriched.get("recent_edits") is None:
        enriched["recent_edits"] = []

    # todos — must be a list
    if enriched.get("todos") is None:
        enriched["todos"] = []

    return enriched


def _safe_active_file_basename(snapshot: ContextSnapshot) -> str:
    """Return a safe display name for the active file, never raising."""
    path = snapshot.active_file or ""
    basename = path.rstrip("/").split("/")[-1]
    return basename if basename else "unknown file"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def save_snapshot(request: SnapshotCreateRequest) -> ContextSnapshot:
    """
    Persist a developer context snapshot, enriched with AI summary + next steps.

    Steps:
      1. Hydrate a ContextSnapshot from the request.
      2. Fix any missing or placeholder snapshot name.
      3. Enrich the context dict so the AI always receives complete data.
      4. Call the AI; fall back to sensible defaults on failure.
      5. Persist to the database.
    """
    snapshot = ContextSnapshot(**request.model_dump())

    # --- Step 1: Fix snapshot name before anything else --------------------
    if _needs_generated_name(snapshot.name):
        snapshot.name = _derive_snapshot_name(snapshot)
        logger.debug("Generated snapshot name: %r", snapshot.name)

    # --- Step 2: Build enriched context for the AI ------------------------
    # Write enriched fields back onto the snapshot so the stored record is
    # consistent with what the AI received — e.g. a None active_file becomes
    # "unknown_file" in both the AI call AND the persisted data_json.
    ai_context = _ensure_ai_context(snapshot.model_dump(mode="json"))
    snapshot.active_file = ai_context["active_file"]
    snapshot.open_files  = ai_context["open_files"]
    snapshot.recent_edits = ai_context["recent_edits"]
    snapshot.todos        = ai_context["todos"]

    logger.info(
        "Generating AI summary for snapshot %r | active_file=%r | open_files=%d | recent_edits=%d | todos=%d",
        snapshot.id,
        ai_context.get("active_file"),
        len(ai_context.get("open_files") or []),
        len(ai_context.get("recent_edits") or []),
        len(ai_context.get("todos") or []),
    )

    # --- Step 3: AI enrichment with graceful fallback ---------------------
    try:
        snapshot.ai_summary = await generate_context_summary(ai_context)
        snapshot.next_steps = await generate_next_steps(ai_context)
        logger.debug("AI enrichment succeeded for snapshot %r", snapshot.id)
    except Exception as exc:
        logger.warning(
            "AI enrichment failed for snapshot %r (%s); using fallback values.",
            snapshot.id,
            exc,
        )
        file_label = _safe_active_file_basename(snapshot)
        snapshot.ai_summary = f"Working in {file_label}"
        snapshot.next_steps = [
            "Review recent changes",
            "Run the test suite",
            "Continue implementation",
        ]

    # --- Step 4: Persist ---------------------------------------------------
    async with AsyncSessionLocal() as db:
        db.add(SnapshotDB(
            id=snapshot.id,
            name=snapshot.name,
            project_path=snapshot.project_path,
            timestamp=snapshot.timestamp,
            data_json=snapshot.model_dump_json(),
        ))
        await db.commit()
        logger.info("Snapshot %r (%r) saved to database.", snapshot.id, snapshot.name)

    return snapshot


async def get_snapshot(snapshot_id: str) -> Optional[ContextSnapshot]:
    """Fetch a single snapshot by ID. Returns None if not found."""
    async with AsyncSessionLocal() as db:
        row = await db.get(SnapshotDB, snapshot_id)
        if row:
            return ContextSnapshot.model_validate_json(row.data_json)
    return None


def _build_demo_request() -> SnapshotCreateRequest:
    """
    Return a SnapshotCreateRequest pre-filled with realistic demo data.

    This is intentionally left as a plain data builder — no DB or AI calls —
    so it stays pure and testable.  The caller (list_snapshots) passes the
    result through save_snapshot(), which runs the full AI enrichment pipeline.
    """
    return SnapshotCreateRequest(
        name="JWT Auth Refactor",
        project_path="/demo/backend",
        active_file="backend/auth/auth.service.ts",
         timestamp=datetime.now(timezone.utc),
        open_files=[
            {"path": "backend/auth/auth.service.ts", "cursor_line": 142},
            {"path": "backend/auth/jwt.util.ts",     "cursor_line": 34},
        ],
        recent_edits=[
            {"file": "auth.service.ts", "line": 142, "timestamp": "2h ago"},
            {"file": "jwt.util.ts",     "line": 34,  "timestamp": "2h 15m ago"},
        ],
        todos=[
            "Add unit tests for validateToken() at line 142",
            "Deploy auth service to staging",
        ],
        tags=["demo", "auth", "backend"],
    )


async def list_snapshots(project_path: Optional[str] = None) -> List[ContextSnapshot]:
    """
    Return all snapshots, optionally filtered by project path, newest first.

    First-run seeding
    -----------------
    When the database contains zero snapshots *and* no project_path filter is
    active, a single realistic demo snapshot is created via save_snapshot() so
    new users land on a populated dashboard rather than a blank screen.
    The seed runs through the full AI enrichment pipeline — same as any real
    snapshot — so the demo data looks authentic.

    Rows whose JSON cannot be parsed are skipped and logged rather than
    crashing the entire listing.
    """
    async with AsyncSessionLocal() as db:
        if project_path:
            stmt = (
                select(SnapshotDB)
                .where(SnapshotDB.project_path == project_path)
                .order_by(SnapshotDB.timestamp.desc())
            )
        else:
            stmt = select(SnapshotDB).order_by(SnapshotDB.timestamp.desc())

        results = await db.execute(stmt)
        rows = results.scalars().all()

    snapshots: List[ContextSnapshot] = []
    for row in rows:
        try:
            snapshots.append(ContextSnapshot.model_validate_json(row.data_json))
        except Exception as exc:
            logger.warning("Could not deserialise snapshot %r: %s", row.id, exc)

    # ── First-run demo seed ──────────────────────────────────────────────────
    # Only seed when the *global* list is empty (no project_path filter) so we
    # don't accidentally seed for every unknown project path.
    if not snapshots:
        logger.info("Database is empty — seeding demo snapshot.")
        try:
            demo = await save_snapshot(_build_demo_request())
            snapshots.append(demo)
            logger.info("Demo snapshot %r created successfully.", demo.id)
        except Exception as exc:
            # Seeding is best-effort: a failure here must never block the API.
            logger.warning("Demo snapshot seeding failed: %s", exc)

    return snapshots


async def delete_snapshot(snapshot_id: str) -> bool:
    """Delete a snapshot by ID. Returns True if it existed, False otherwise."""
    async with AsyncSessionLocal() as db:
        row = await db.get(SnapshotDB, snapshot_id)
        if row:
            await db.delete(row)
            await db.commit()
            logger.info("Snapshot %r deleted.", snapshot_id)
            return True
    return False


async def get_resume_briefing(snapshot_id: str, time_away_minutes: int = 60) -> str:
    """
    Generate an AI re-orientation briefing for a developer returning to a saved context.
    Falls back to a static summary if the AI call fails or the snapshot is missing.
    """
    snapshot = await get_snapshot(snapshot_id)
    if not snapshot:
        logger.warning("get_resume_briefing: snapshot %r not found.", snapshot_id)
        return "Snapshot not found."

    try:
        briefing = await generate_resume_briefing(
            snapshot.model_dump(mode="json"),
            time_away_minutes,
        )
        logger.debug("Resume briefing generated for snapshot %r.", snapshot_id)
        return briefing
    except Exception as exc:
        logger.warning(
            "Resume briefing generation failed for snapshot %r (%s); using fallback.",
            snapshot_id,
            exc,
        )
        label = snapshot.ai_summary or snapshot.name or "your last session"
        return f"Welcome back! You were working on: {label}"