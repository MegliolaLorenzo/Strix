import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from schemas import CheckRequest, Verdict
from agents.graph import analyze_claim
from services.cache import cache
from database import save_check

router = APIRouter()


@router.post("/api/check", response_model=Verdict)
async def fact_check(request: CheckRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")

    # Check cache first
    cached = cache.get(text)
    if cached:
        return cached

    # Multi-agent analysis (search + reasoning are handled inside the graph)
    start = time.monotonic()
    analysis = await analyze_claim(text)
    total_ms = int((time.monotonic() - start) * 1000)

    # Split timing roughly: 40% search, 60% analysis (approximation)
    search_ms = int(total_ms * 0.4)
    analysis_ms = total_ms - search_ms

    verdict = {
        "id": str(uuid.uuid4()),
        "claim": text,
        "verdict": analysis.get("verdict", "Needs Context"),
        "confidence": max(0, min(100, analysis.get("confidence", 50))),
        "explanation": analysis.get("explanation", "Analysis could not be completed."),
        "sources": analysis.get("sources", [])[:8],
        "rewrite_suggestion": analysis.get("rewrite_suggestion"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "search_time_ms": search_ms,
        "analysis_time_ms": analysis_ms,
    }

    await save_check(verdict)
    cache.set(text, verdict)

    return verdict
