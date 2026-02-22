from __future__ import annotations

import aiosqlite
import json
from config import settings

DB_PATH = settings.strix_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id TEXT PRIMARY KEY,
    claim TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    sources TEXT NOT NULL,
    rewrite_suggestion TEXT,
    agent TEXT,
    checked_at TEXT NOT NULL,
    search_time_ms INTEGER NOT NULL,
    analysis_time_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checks_verdict ON checks(verdict);
CREATE INDEX IF NOT EXISTS idx_checks_checked_at ON checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_checks_confidence ON checks(confidence);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        # Migrate: add agent column if missing (for existing DBs)
        try:
            await db.execute("ALTER TABLE checks ADD COLUMN agent TEXT")
        except Exception:
            pass
        await db.commit()


async def save_check(verdict: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO checks (id, claim, verdict, confidence, explanation,
               sources, rewrite_suggestion, agent, checked_at, search_time_ms, analysis_time_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                verdict["id"],
                verdict["claim"],
                verdict["verdict"],
                verdict["confidence"],
                verdict["explanation"],
                json.dumps(verdict["sources"]),
                verdict.get("rewrite_suggestion"),
                verdict.get("agent"),
                verdict["checked_at"],
                verdict["search_time_ms"],
                verdict["analysis_time_ms"],
            ),
        )
        await db.commit()


async def get_checks(
    verdict: str | None = None,
    min_confidence: int | None = None,
    max_confidence: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params = []

    if verdict:
        conditions.append("verdict = ?")
        params.append(verdict)
    if min_confidence is not None:
        conditions.append("confidence >= ?")
        params.append(min_confidence)
    if max_confidence is not None:
        conditions.append("confidence <= ?")
        params.append(max_confidence)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM checks {where} ORDER BY checked_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    **dict(row),
                    "sources": json.loads(row["sources"]),
                }
                for row in rows
            ]


async def get_analytics() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Total checks
        async with db.execute("SELECT COUNT(*) as cnt FROM checks") as cur:
            total = (await cur.fetchone())["cnt"]

        # Verdict distribution
        async with db.execute(
            "SELECT verdict, COUNT(*) as cnt FROM checks GROUP BY verdict"
        ) as cur:
            verdict_dist = {row["verdict"]: row["cnt"] for row in await cur.fetchall()}

        # Daily counts (last 30 days)
        async with db.execute(
            """SELECT DATE(checked_at) as day, COUNT(*) as cnt
               FROM checks GROUP BY DATE(checked_at)
               ORDER BY day DESC LIMIT 30"""
        ) as cur:
            daily = [dict(row) for row in await cur.fetchall()]

        # Top claims (most repeated, grouped by similarity — simplified: exact match)
        async with db.execute(
            """SELECT claim, verdict, confidence, COUNT(*) as cnt
               FROM checks GROUP BY claim
               HAVING cnt > 1 ORDER BY cnt DESC LIMIT 10"""
        ) as cur:
            top_claims = [dict(row) for row in await cur.fetchall()]

        # Average confidence
        async with db.execute(
            "SELECT AVG(confidence) as avg_conf FROM checks"
        ) as cur:
            avg_conf = (await cur.fetchone())["avg_conf"] or 0

        # Source domain distribution
        async with db.execute("SELECT sources FROM checks") as cur:
            domain_counts: dict[str, int] = {}
            for row in await cur.fetchall():
                for source in json.loads(row["sources"]):
                    domain = source.get("domain", "unknown")
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_checks": total,
            "verdict_distribution": verdict_dist,
            "daily_counts": daily,
            "top_claims": top_claims,
            "avg_confidence": round(avg_conf, 1),
            "source_domains": dict(
                sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            ),
        }
