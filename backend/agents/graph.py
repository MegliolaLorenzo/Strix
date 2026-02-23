"""STRIX fact-checking agent.

Architecture:
    Single ReAct agent — Claude Sonnet 4.5
    Selects tools autonomously based on the claim type:
        - tavily_search    : general web search
        - gnews_search     : recent news articles
        - arxiv_search     : scientific papers
        - wikipedia_search : encyclopedic facts
"""

from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlparse

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import create_react_agent

from agents.tools import arxiv_search, gnews_search, tavily_search, wikipedia_search
from config import settings

# ---------------------------------------------------------------------------
# Verdict criteria
# ---------------------------------------------------------------------------

VERDICT_CRITERIA = """
Verdict definitions (use these EXACTLY):
- "Supported": The claim is factually correct. Use when evidence confirms it, OR when it is a universally established fact that your knowledge confirms — even if search results don't directly address it.
- "Unsupported": The claim is factually wrong or actively contradicted by credible evidence. ONLY use this when the claim is demonstrably false.
- "Misleading": The claim contains some truth but is deceptively framed, uses cherry-picked data, or omits crucial context that materially changes its meaning.
- "Needs Context": The claim is partially true but requires important qualifications to avoid misunderstanding.

Confidence scoring:
- 90-100: Universally known fact or overwhelming evidence
- 70-89: Strong evidence from multiple credible sources
- 50-69: Moderate evidence, some ambiguity
- 30-49: Weak or conflicting evidence
- 0-29: Very uncertain, insufficient data

Key rules:
- For well-established, uncontested facts, rely on your knowledge if search results are unhelpful.
- "Unsupported" is reserved for demonstrably false claims — not for claims lacking search hits.
- Do NOT invent URLs or sources. If no relevant sources exist, return an empty sources array.
- rewrite_suggestion should be null if the original claim is accurate.
- For time-sensitive claims (prices, current events, elections, product specs, "latest/current"), always use web/news tools.
"""

# ---------------------------------------------------------------------------
# Agent prompt
# ---------------------------------------------------------------------------

AGENT_PROMPT = f"""You are STRIX, an expert fact-checker. Analyse claims and produce rigorous, source-backed verdicts.

## Tools
Choose tools based on the claim type — do not use all of them every time:
- **tavily_search**: general web search — use for most claims
- **gnews_search**: recent news articles — use for current events, politics, breaking news
- **arxiv_search**: scientific papers — use for medical, scientific, or research claims
- **wikipedia_search**: encyclopedic facts — use for historical facts, biographies, geography

## Workflow
1. Assess the claim.
2. For universally established facts (birthplaces, capitals, well-known history), answer from knowledge — no tool call needed.
3. For everything else, call ONE tool. Call a second only if the first result is clearly insufficient and the claim spans two distinct domains. Never call more than 2 tools.
4. After receiving tool results, immediately write the verdict JSON. Do not call more tools.

## Output
Your final response must be ONLY a valid JSON object — no markdown, no extra text:
{{
  "verdict": "Supported" | "Unsupported" | "Misleading" | "Needs Context",
  "confidence": <integer 0-100>,
  "explanation": "<2-3 clear sentences explaining the verdict>",
  "sources": [
    {{
      "title": "<article title>",
      "url": "<source URL>",
      "domain": "<domain name>",
      "relevance": "<one sentence on how this source relates to the claim>"
    }}
  ],
  "rewrite_suggestion": "<a more accurate way to state the claim, or null if accurate>"
}}

{VERDICT_CRITERIA}

CRITICAL: Your final response must be ONLY the JSON object above. No preamble, no explanation outside the JSON."""

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------


def _build_model() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        api_key=settings.anthropic_api_key,
        max_tokens=900,
    )


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------


def build_graph():
    return create_react_agent(
        model=_build_model(),
        tools=[tavily_search, gnews_search, arxiv_search, wikipedia_search],
        prompt=AGENT_PROMPT,
    )


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output, handling markdown fences."""
    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {
        "verdict": "Needs Context",
        "confidence": 30,
        "explanation": text[:500] if text else "Analysis could not produce a structured result.",
        "sources": [],
        "rewrite_suggestion": None,
    }


_MD_URL_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\)\s]+)\)')
_RAW_URL_RE = re.compile(r'URL:\s*(https?://\S+)')


def _get_content(msg) -> str:
    content = getattr(msg, "content", None)
    if not content:
        return ""
    if isinstance(content, list):
        parts = [
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ]
        return " ".join(parts).strip()
    return str(content).strip()


def _extract_sources_from_tool_results(messages: list) -> list[dict]:
    """Parse raw tool outputs to build a source list.

    The LLM often drops URLs when summarising, so we extract them directly
    from ToolMessage payloads which always contain the raw tool output.
    """
    sources: list[dict] = []
    seen: set[str] = set()

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = _get_content(msg)
        if not content:
            continue

        for title, url in _MD_URL_RE.findall(content):
            if url not in seen:
                seen.add(url)
                sources.append({
                    "title": title.strip(),
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "relevance": "Found in search results",
                })

        for url in _RAW_URL_RE.findall(content):
            url = url.rstrip(".")
            if url not in seen:
                seen.add(url)
                domain = urlparse(url).netloc
                idx = content.find(url)
                snippet = content[max(0, idx - 120):idx]
                title_match = re.search(r'\*\*([^\*]+)\*\*\s*$', snippet)
                title = title_match.group(1).strip() if title_match else domain
                sources.append({
                    "title": title,
                    "url": url,
                    "domain": domain,
                    "relevance": "Found in search results",
                })

    return sources[:8]


TIMEOUT_SECONDS = 30


async def _run_graph(claim: str) -> dict:
    graph = get_graph()

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": f'Fact-check this claim: "{claim}"'}]},
        config={"recursion_limit": 6},
    )

    messages = result.get("messages", [])
    tool_sources = _extract_sources_from_tool_results(messages)

    def _finalise(verdict: dict) -> dict:
        if not verdict.get("sources"):
            verdict["sources"] = tool_sources
        return verdict

    for msg in reversed(messages):
        content = _get_content(msg)
        if not content:
            continue
        if '"verdict"' in content:
            return _finalise(_extract_json(content))

    for msg in reversed(messages):
        content = _get_content(msg)
        if len(content) > 100 and "{" in content:
            return _finalise(_extract_json(content))

    raise RuntimeError("Graph completed without producing a verdict JSON")


_FALLBACK_PROMPT = """\
You are STRIX, an expert fact-checker. Analyse the claim below and reply with ONLY a valid JSON object — no markdown, no extra text.

Claim: "{claim}"

{criteria}

JSON format:
{{
  "verdict": "Supported" | "Unsupported" | "Misleading" | "Needs Context",
  "confidence": <integer 0-100>,
  "explanation": "<2-3 clear sentences>",
  "sources": [],
  "rewrite_suggestion": "<more accurate phrasing, or null>"
}}"""


async def _direct_analysis(claim: str) -> dict:
    """Single Claude call, no tools. Emergency fallback only."""
    from langchain_core.messages import HumanMessage

    model = _build_model()
    prompt = _FALLBACK_PROMPT.format(claim=claim, criteria=VERDICT_CRITERIA)
    response = await model.ainvoke([HumanMessage(content=prompt)])
    return _extract_json(_get_content(response))


async def analyze_claim(claim: str) -> dict:
    """Run the fact-checking agent on a claim and return a verdict dict."""
    clean_claim = " ".join(claim.split())

    try:
        return await asyncio.wait_for(_run_graph(clean_claim), timeout=TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, Exception):
        pass

    try:
        return await asyncio.wait_for(_direct_analysis(clean_claim), timeout=15)
    except Exception:
        pass

    return {
        "verdict": "Unsupported",
        "confidence": 0,
        "explanation": "Analysis service is temporarily unavailable. Please try again.",
        "sources": [],
        "rewrite_suggestion": None,
    }
