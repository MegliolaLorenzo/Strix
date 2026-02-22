"""STRIX multi-agent fact-checking graph.

Architecture:
    Supervisor (orchestrator)
        ├── political_analyst   — politics, elections, government, geopolitics
        ├── science_verifier    — science, health, medicine, environment, technology
        ├── finance_analyst     — economics, markets, business, trade
        ├── general_knowledge   — history, geography, culture, biography, sports
        └── news_verifier       — breaking news, current events, trending topics

Each specialist gathers evidence with its tools, reports findings.
The supervisor synthesises a final structured verdict.
"""

from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlparse

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from agents.tools import (
    arxiv_search,
    gnews_search,
    tavily_search,
    web_fetch,
    wikipedia_search,
)
from config import settings

# ---------------------------------------------------------------------------
# Shared verdict criteria — injected into the supervisor prompt
# ---------------------------------------------------------------------------

VERDICT_CRITERIA = """
Verdict definitions (use these EXACTLY):
- "Supported": The claim is factually correct. Use when evidence confirms it, OR when it is a universally established fact (birthplace, nationality, well-documented historical event, scientific consensus) that your knowledge confirms — even if search results don't directly address it.
- "Unsupported": The claim is factually wrong or actively contradicted by credible evidence. ONLY use this when the claim is demonstrably false. Do NOT use it simply because search results were sparse or inconclusive.
- "Misleading": The claim contains some truth but is deceptively framed, uses cherry-picked data, or omits crucial context that materially changes its meaning.
- "Needs Context": The claim is partially true or accurate in some interpretations, but requires important qualifications to avoid misunderstanding.

Confidence scoring:
- 90-100: Universally known fact or overwhelming evidence
- 70-89: Strong evidence from multiple credible sources
- 50-69: Moderate evidence, some ambiguity
- 30-49: Weak or conflicting evidence
- 0-29: Very uncertain, insufficient data

Key rules:
- For well-established, uncontested facts, rely on your knowledge if search results are unhelpful. Do not penalize a true claim for lack of search coverage.
- "Unsupported" is reserved for claims that are demonstrably false — not for claims that merely lack search hits.
- Do NOT invent URLs or sources. If no relevant sources exist, return an empty sources array.
- rewrite_suggestion should be null if the original claim is accurate.
- Speed policy: if the claim is a universally established fact, avoid external tool calls and answer from reliable background knowledge.
- Time-sensitive policy: for product releases/specs, prices, "latest/current/today", elections, or leadership changes, you MUST use web/news tools before finalizing.
"""

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------


def _build_supervisor_model() -> ChatAnthropic:
    """Sonnet 4.5 for the supervisor — best reasoning model for verdict synthesis."""
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        api_key=settings.anthropic_api_key,
        max_tokens=900,
    )


def _build_specialist_model() -> ChatAnthropic:
    """Haiku 4.5 for specialists — they only search & summarise, not reason deeply.
    2x faster than Sonnet 4, matches Sonnet 4 coding quality at 1/3 the cost."""
    return ChatAnthropic(
        model="claude-haiku-4-5",
        api_key=settings.anthropic_api_key,
        max_tokens=500,
    )


# ---------------------------------------------------------------------------
# Specialist agent prompts
# ---------------------------------------------------------------------------

POLITICAL_PROMPT = (
    "You are a political fact-checking specialist. "
    "Your expertise covers elections, government policy, legislation, geopolitics, "
    "international relations, political figures, and political history.\n\n"
    "When given a claim, use your tools to gather evidence. Search for official records, "
    "government sources, and reputable news outlets. Report your findings clearly:\n"
    "- What evidence you found (with specific sources)\n"
    "- Whether the evidence supports or contradicts the claim\n"
    "- Any important context or nuance\n"
    "Be thorough but concise. Default to one tool call; use a second only if necessary."
)

SCIENCE_PROMPT = (
    "You are a science and health fact-checking specialist. "
    "Your expertise covers scientific research, medical claims, environmental science, "
    "technology, physics, biology, chemistry, and academic studies.\n\n"
    "When given a claim, use your tools to gather evidence. Search for peer-reviewed research, "
    "scientific consensus, and authoritative sources like WHO, CDC, NASA, etc. "
    "Report your findings clearly:\n"
    "- What evidence you found (with specific sources)\n"
    "- Whether the scientific consensus supports or contradicts the claim\n"
    "- Any important caveats or nuance in the research\n"
    "Be thorough but concise. Default to one tool call; use a second only if necessary."
)

FINANCE_PROMPT = (
    "You are an economics and finance fact-checking specialist. "
    "Your expertise covers economic indicators, financial markets, business news, "
    "trade policy, GDP, employment statistics, corporate facts, and monetary policy.\n\n"
    "When given a claim, use your tools to gather evidence. Search for official statistics, "
    "central bank reports, financial news, and authoritative economic data. "
    "Report your findings clearly:\n"
    "- What evidence you found (with specific sources)\n"
    "- Whether the data supports or contradicts the claim\n"
    "- Any important context about timeframes, methodology, or definitions\n"
    "Be thorough but concise. Default to one tool call; use a second only if necessary."
)

GENERAL_PROMPT = (
    "You are a general knowledge fact-checking specialist. "
    "Your expertise covers history, geography, culture, biographical facts, sports, "
    "entertainment, languages, and everyday factual claims.\n\n"
    "When given a claim, use your tools to gather evidence. Start with Wikipedia for "
    "encyclopedic facts, then use web search for additional verification. "
    "Report your findings clearly:\n"
    "- What evidence you found (with specific sources)\n"
    "- Whether the evidence supports or contradicts the claim\n"
    "- Any important distinctions or context\n"
    "Be thorough but concise. For universally established facts, you may answer without tool calls."
)

NEWS_PROMPT = (
    "You are a current events fact-checking specialist. "
    "Your expertise covers breaking news, recent events, trending topics, "
    "media reports, and real-time developments.\n\n"
    "When given a claim, use your tools to gather evidence. Search recent news articles "
    "and authoritative sources. If needed, fetch full article content for deeper analysis. "
    "Report your findings clearly:\n"
    "- What evidence you found (with specific sources)\n"
    "- Whether recent reporting supports or contradicts the claim\n"
    "- Any evolving aspects of the story\n"
    "Be thorough but concise. Default to one tool call; use a second only if necessary."
)

# ---------------------------------------------------------------------------
# Supervisor prompt
# ---------------------------------------------------------------------------

SUPERVISOR_PROMPT = f"""You are STRIX, an expert fact-checking orchestrator. Your job is to analyse claims and produce rigorous, structured verdicts.

## Workflow
1. Read the claim carefully.
2. Decide which specialist(s) to consult:
   - political_analyst: politics, elections, government, geopolitics
   - science_verifier: science, health, medicine, environment, technology
   - finance_analyst: economics, markets, business, trade
   - general_knowledge: history, geography, culture, biography, sports
   - news_verifier: breaking news, current events, trending topics
3. Route the claim to the most relevant specialist. You may consult multiple if the claim spans domains.
   Default behavior: consult ONE specialist only. Consult multiple specialists only when the claim truly mixes domains.
4. After receiving specialist findings, synthesise a final verdict.

## Output format
Your FINAL response (after consulting specialists) must be ONLY a valid JSON object — no markdown, no explanation outside the JSON:
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

CRITICAL: After receiving specialist findings, you MUST respond with ONLY the JSON verdict object as your final message. Do NOT transfer to another agent after synthesis — just output the JSON directly. Be precise, objective, and concise."""


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------


def build_graph():
    """Construct and compile the STRIX multi-agent graph.

    Model split:
    - Specialists use claude-haiku (fast, ~10x cheaper) — they only gather evidence.
    - Supervisor uses claude-sonnet (full reasoning) — synthesises the final verdict.
    """
    specialist_model = _build_specialist_model()
    supervisor_model = _build_supervisor_model()

    political_agent = create_react_agent(
        model=specialist_model,
        tools=[tavily_search, gnews_search],
        name="political_analyst",
        prompt=POLITICAL_PROMPT,
    )

    science_agent = create_react_agent(
        model=specialist_model,
        tools=[tavily_search, arxiv_search],
        name="science_verifier",
        prompt=SCIENCE_PROMPT,
    )

    finance_agent = create_react_agent(
        model=specialist_model,
        tools=[tavily_search, gnews_search],
        name="finance_analyst",
        prompt=FINANCE_PROMPT,
    )

    general_agent = create_react_agent(
        model=specialist_model,
        tools=[wikipedia_search, tavily_search],
        name="general_knowledge",
        prompt=GENERAL_PROMPT,
    )

    news_agent = create_react_agent(
        model=specialist_model,
        tools=[gnews_search, tavily_search, web_fetch],
        name="news_verifier",
        prompt=NEWS_PROMPT,
    )

    supervisor = create_supervisor(
        agents=[political_agent, science_agent, finance_agent, general_agent, news_agent],
        model=supervisor_model,
        prompt=SUPERVISOR_PROMPT,
    )

    return supervisor.compile()


# Lazy singleton — built on first use
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output, handling markdown fences."""
    text = text.strip()

    # Strip markdown code block
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback
    return {
        "verdict": "Needs Context",
        "confidence": 30,
        "explanation": text[:500] if text else "Analysis could not produce a structured result.",
        "sources": [],
        "rewrite_suggestion": None,
    }


# Regex patterns to extract URLs from tool outputs
_MD_URL_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\)\s]+)\)')   # [Title](url)
_RAW_URL_RE = re.compile(r'URL:\s*(https?://\S+)')                 # URL: https://...


def _extract_sources_from_tool_results(messages: list) -> list[dict]:
    """Parse raw tool outputs to build a source list.

    The LLM often drops URLs when summarising findings, so we extract them
    directly from ToolMessage payloads — which always contain the raw tool output.
    """
    sources: list[dict] = []
    seen: set[str] = set()

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = _get_content(msg)
        if not content:
            continue

        # [Title](url) — format used by tavily_search and gnews_search
        for title, url in _MD_URL_RE.findall(content):
            if url not in seen:
                seen.add(url)
                domain = urlparse(url).netloc
                sources.append({
                    "title": title.strip(),
                    "url": url,
                    "domain": domain,
                    "relevance": "Found in search results",
                })

        # URL: https://... — format used by wikipedia_search and arxiv_search
        for url in _RAW_URL_RE.findall(content):
            url = url.rstrip(".")
            if url not in seen:
                seen.add(url)
                domain = urlparse(url).netloc
                # Try to find a title near this URL in the content
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


AGENT_NAMES = {
    "political_analyst", "science_verifier", "finance_analyst",
    "general_knowledge", "news_verifier",
}

AGENT_LABELS = {
    "political_analyst": "Political Analyst",
    "science_verifier": "Science Verifier",
    "finance_analyst": "Finance Analyst",
    "general_knowledge": "General Knowledge",
    "news_verifier": "News Verifier",
}


def _detect_agent(messages: list) -> str | None:
    """Detect which specialist agent was invoked from the message history.

    Checks three places where langgraph-supervisor records the routing decision:
    1. AIMessage.tool_calls — supervisor's transfer_to_<agent> call
    2. ToolMessage.name    — name of the transfer tool that was invoked
    3. AIMessage.name      — agent name set by create_react_agent
    """
    for msg in messages:
        # 1. tool_calls on AIMessage (supervisor calling transfer_to_*)
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                for agent_name in AGENT_NAMES:
                    if agent_name in name:
                        return AGENT_LABELS.get(agent_name, agent_name)

        # 2. ToolMessage.name — the tool that was executed
        if isinstance(msg, ToolMessage):
            tm_name = getattr(msg, "name", "") or ""
            for agent_name in AGENT_NAMES:
                if agent_name in tm_name:
                    return AGENT_LABELS.get(agent_name, agent_name)

        # 3. AIMessage.name — set by create_react_agent for specialist messages
        msg_name = getattr(msg, "name", None)
        if msg_name and msg_name in AGENT_NAMES:
            return AGENT_LABELS.get(msg_name, msg_name)

    return None


def _get_content(msg) -> str:
    """Extract text content from a LangChain message."""
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


def _is_time_sensitive_claim(claim: str) -> bool:
    c = claim.lower()
    markers = [
        "latest", "current", "today", "recent", "just released", "just announced",
        "just dropped", "just made", "just launched", "released", "release",
        "launch", "launched", "dropped", "announced", "preview", "early access",
        "shipping", "iphone", "ios", "android", "pixel", "samsung", "macbook",
        "price", "camera", "zoom", "spec", "rumor", "leak", "update", "new feature",
        "election", "president", "prime minister", "ceo", "inflation", "gdp",
        "obsolete", "breaking", "just", "now available", "rolled out",
    ]
    if any(m in c for m in markers):
        return True
    return re.search(r"\b20[2-9]\d\b", c) is not None


TIMEOUT_SECONDS = 30  # hard cap — agents need time; fallback only on genuine crash


async def _run_graph(claim: str) -> dict:
    """Internal: invoke the graph and extract the verdict dict."""
    graph = get_graph()
    time_sensitive = _is_time_sensitive_claim(claim)

    if time_sensitive:
        user_prompt = (
            f'Fact-check this claim: "{claim}"\n'
            "This is time-sensitive. You MUST use live web/news tools and cite current sources. "
            "Do not answer from memory or speculation."
        )
        recursion_limit = 12
    else:
        user_prompt = f'Fact-check this claim: "{claim}"'
        recursion_limit = 8

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": user_prompt}]},
        config={"recursion_limit": recursion_limit},
    )

    messages = result.get("messages", [])
    agent_used = _detect_agent(messages)

    # Extract sources directly from tool outputs (LLMs often drop URLs when summarising)
    tool_sources = _extract_sources_from_tool_results(messages)

    def _finalise(verdict: dict) -> dict:
        verdict["agent"] = agent_used
        # If the LLM returned no sources, inject what we extracted from tool results
        if not verdict.get("sources"):
            verdict["sources"] = tool_sources
        return verdict

    # Walk backwards to find a message containing a verdict JSON
    for msg in reversed(messages):
        content = _get_content(msg)
        if not content or ("transfer" in content.lower() and len(content) < 100):
            continue
        if '"verdict"' in content:
            return _finalise(_extract_json(content))

    # Second pass: any substantial message with JSON
    for msg in reversed(messages):
        content = _get_content(msg)
        if len(content) > 100 and "{" in content:
            return _finalise(_extract_json(content))

    # Graph ran but produced no parseable JSON — raise so caller can fallback
    raise RuntimeError("Graph completed without producing a verdict JSON")


_FALLBACK_PROMPT = """\
You are STRIX, an expert fact-checker. Analyse the claim below and reply with ONLY a valid JSON object — no markdown, no extra text.

Claim: "{claim}"

{criteria}

JSON format (reply with THIS and nothing else):
{{
  "verdict": "Supported" | "Unsupported" | "Misleading" | "Needs Context",
  "confidence": <integer 0-100>,
  "explanation": "<2-3 clear sentences>",
  "sources": [],
  "rewrite_suggestion": "<more accurate phrasing, or null if claim is accurate>"
}}"""


async def _direct_analysis(claim: str) -> dict:
    """Single Claude Sonnet call, no tools, no agent overhead.

    Used as fallback when the multi-agent graph fails or times out.
    Always returns a real verdict based on Claude's training knowledge.
    """
    from langchain_core.messages import HumanMessage

    model = _build_supervisor_model()
    prompt = _FALLBACK_PROMPT.format(claim=claim, criteria=VERDICT_CRITERIA)
    response = await model.ainvoke([HumanMessage(content=prompt)])
    content = _get_content(response)
    result = _extract_json(content)
    result["agent"] = "Direct Analysis"
    return result


async def analyze_claim(claim: str) -> dict:
    """Run the multi-agent graph on a claim and return a verdict dict.

    Strategy:
    1. Always run the full multi-agent pipeline (tools + specialist routing).
    2. Only on genuine crash (bad model, network error, etc.) fall back to a
       direct single-model call — so a real verdict is always returned.
    3. Timeout is generous (TIMEOUT_SECONDS) so agents have time to complete.
    """
    clean_claim = " ".join(claim.split())  # normalise multiline/emoji text

    # --- Primary: full multi-agent graph (always attempted) ---
    try:
        return await asyncio.wait_for(_run_graph(clean_claim), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        # Agents took too long — fall through to direct analysis so user gets an answer
        pass
    except Exception:
        # Graph crash (bad model name, API error, recursion, etc.) — fall through
        pass

    # --- Emergency fallback: direct Claude call (no agents, always fast) ---
    # Only reached if the graph itself failed — should be rare with correct setup.
    try:
        return await asyncio.wait_for(_direct_analysis(clean_claim), timeout=15)
    except Exception:
        pass

    # Absolute last resort — practically unreachable
    return {
        "verdict": "Unsupported",
        "confidence": 0,
        "explanation": "Analysis service is temporarily unavailable. Please try again.",
        "sources": [],
        "rewrite_suggestion": None,
        "agent": None,
    }
