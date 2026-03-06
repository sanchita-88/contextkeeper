from ai_service import classify_interruption
from models import InterruptionRequest, InterruptionResponse
from database import AsyncSessionLocal, InterruptionLogDB
from datetime import datetime

async def triage(request: InterruptionRequest) -> InterruptionResponse:
    """Classify an interruption and generate an auto-reply."""
    result = await classify_interruption(
        request.message,
        request.source,
        request.current_context
    )
    
    response = InterruptionResponse(
        priority=result.get("priority", "deferrable"),
        reason=result.get("reason", "Classification unavailable"),
        auto_reply=result.get("auto_reply", ""),
        defer_duration_minutes=result.get("defer_duration_minutes", 90),
        action_required=result.get("action_required", "Review when available"),
    )
    
    # Log to database
    async with AsyncSessionLocal() as db:
        db.add(InterruptionLogDB(
            timestamp=datetime.utcnow(),
            message=request.message[:500],
            source=request.source,
            priority=response.priority,
            auto_reply=response.auto_reply[:500],
        ))
        await db.commit()
    
    return response

async def get_stats() -> dict:
    from sqlalchemy import select, func
    from database import InterruptionLogDB
    
    async with AsyncSessionLocal() as db:
        # Total today
        today = datetime.utcnow().date()
        stmt = select(InterruptionLogDB).where(
            func.date(InterruptionLogDB.timestamp) == today
        )
        results = await db.execute(stmt)
        rows = results.scalars().all()
        
        by_priority = {"critical": 0, "important": 0, "deferrable": 0}
        by_source = {}
        
        for row in rows:
            p = row.priority.lower()
            if p in by_priority:
                by_priority[p] += 1
            by_source[row.source] = by_source.get(row.source, 0) + 1
        
        return {
            "total_today": len(rows),
            "by_priority": by_priority,
            "by_source": by_source,
            "focus_time_saved_minutes": by_priority["deferrable"] * 90,
        }
