from fastapi import APIRouter, Query
from typing import Optional

from database import get_checks, get_analytics

router = APIRouter()


@router.get("/api/checks")
async def list_checks(
    verdict: Optional[str] = Query(None),
    min_confidence: Optional[int] = Query(None, ge=0, le=100),
    max_confidence: Optional[int] = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await get_checks(
        verdict=verdict,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        limit=limit,
        offset=offset,
    )


@router.get("/api/analytics")
async def analytics():
    return await get_analytics()
