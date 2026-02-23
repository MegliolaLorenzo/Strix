from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CheckRequest(BaseModel):
    text: str


class Source(BaseModel):
    title: str
    url: str
    domain: str
    relevance: str


class Verdict(BaseModel):
    id: str
    claim: str
    verdict: str  # Supported | Unsupported | Misleading | Needs Context
    confidence: int  # 0-100
    explanation: str
    sources: list[Source]
    rewrite_suggestion: Optional[str] = None
    checked_at: str
    search_time_ms: int
    analysis_time_ms: int


class CheckListParams(BaseModel):
    verdict: Optional[str] = None
    min_confidence: Optional[int] = None
    max_confidence: Optional[int] = None
    limit: int = 50
    offset: int = 0


class AnalyticsResponse(BaseModel):
    total_checks: int
    verdict_distribution: dict[str, int]
    daily_counts: list[dict]
    top_claims: list[dict]
    avg_confidence: float
    source_domains: dict[str, int]
