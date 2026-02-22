"""LangChain tools for STRIX fact-checking agents.

Each tool wraps a free API and returns formatted text for the LLM to analyze.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

from config import settings

# ---------------------------------------------------------------------------
# Tavily Web Search (free tier: 1 000 req/month)
# ---------------------------------------------------------------------------

@tool
async def tavily_search(query: str) -> str:
    """Search the web for current, factual information using Tavily.
    Use this for any claim that requires up-to-date web evidence."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": 3,
                    "include_answer": False,
                    "include_raw_content": False,
                    "search_depth": "basic",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for r in data.get("results", []):
            domain = urlparse(r.get("url", "")).netloc
            results.append(
                f"[{r.get('title', 'Untitled')}]({r.get('url', '')})\n"
                f"Domain: {domain}\n"
                f"Content: {r.get('content', 'No content')[:500]}"
            )
        return "\n\n---\n\n".join(results) if results else "No web results found."
    except Exception as e:
        return f"Web search failed: {e}"


# ---------------------------------------------------------------------------
# GNews Search (free tier: 100 req/day)
# ---------------------------------------------------------------------------

@tool
async def gnews_search(query: str) -> str:
    """Search recent news articles using GNews.
    Use this for claims about current events, politics, or breaking news."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q": query,
                    "lang": "en",
                    "max": 3,
                    "apikey": settings.gnews_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for a in data.get("articles", []):
            domain = urlparse(a.get("source", {}).get("url", "")).netloc
            results.append(
                f"[{a.get('title', 'Untitled')}]({a.get('url', '')})\n"
                f"Domain: {domain}\n"
                f"Published: {a.get('publishedAt', 'Unknown')}\n"
                f"Content: {a.get('description', 'No description')[:400]}"
            )
        return "\n\n---\n\n".join(results) if results else "No news results found."
    except Exception as e:
        return f"News search failed: {e}"


# ---------------------------------------------------------------------------
# Wikipedia Search (completely free, no API key)
# ---------------------------------------------------------------------------

@tool
async def wikipedia_search(query: str) -> str:
    """Search Wikipedia for encyclopedic, factual information.
    Use this for historical facts, biographical data, geography, science, and general knowledge."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Step 1: search for relevant articles
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 2,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            search_results = resp.json().get("query", {}).get("search", [])

            if not search_results:
                return "No Wikipedia articles found."

            # Step 2: get summaries for top results
            summaries = []
            for sr in search_results:
                title = sr["title"]
                summary_resp = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                    headers={"User-Agent": "STRIX/1.0 (fact-checking tool)"},
                )
                if summary_resp.status_code == 200:
                    data = summary_resp.json()
                    summaries.append(
                        f"**{data.get('title', title)}**\n"
                        f"URL: https://en.wikipedia.org/wiki/{title.replace(' ', '_')}\n"
                        f"{data.get('extract', 'No extract available')[:600]}"
                    )

            return "\n\n---\n\n".join(summaries) if summaries else "No Wikipedia summaries available."
    except Exception as e:
        return f"Wikipedia search failed: {e}"


# ---------------------------------------------------------------------------
# arXiv Search (completely free, no API key)
# ---------------------------------------------------------------------------

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


@tool
async def arxiv_search(query: str) -> str:
    """Search arXiv for scientific papers and research.
    Use this for claims about scientific findings, medical research, or academic studies."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "http://export.arxiv.org/api/query",
                params={
                    "search_query": f"all:{query}",
                    "max_results": "2",
                    "sortBy": "relevance",
                },
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        entries = root.findall("atom:entry", ARXIV_NS)

        results = []
        for entry in entries:
            title_el = entry.find("atom:title", ARXIV_NS)
            summary_el = entry.find("atom:summary", ARXIV_NS)
            link_el = entry.find("atom:id", ARXIV_NS)

            title = title_el.text.strip().replace("\n", " ") if title_el is not None else "Untitled"
            summary = summary_el.text.strip()[:400] if summary_el is not None else "No abstract"
            url = link_el.text.strip() if link_el is not None else ""

            results.append(f"**{title}**\nURL: {url}\nAbstract: {summary}")

        return "\n\n---\n\n".join(results) if results else "No arXiv papers found."
    except Exception as e:
        return f"arXiv search failed: {e}"


# ---------------------------------------------------------------------------
# Web Fetch (free — just HTTP)
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and extract readable text."""

    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.SKIP_TAGS:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_text(self) -> str:
        return " ".join(self._parts)


@tool
async def web_fetch(url: str) -> str:
    """Fetch a web page and extract its text content.
    Use this to read the full content of a specific article or source URL."""
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "STRIX/1.0 (fact-checking tool)"},
            )
            resp.raise_for_status()

        extractor = _HTMLTextExtractor()
        extractor.feed(resp.text)
        text = extractor.get_text()

        # Truncate to avoid overwhelming the LLM
        if len(text) > 3000:
            text = text[:3000] + "... [truncated]"

        return f"Content from {url}:\n\n{text}" if text else "Could not extract text from page."
    except Exception as e:
        return f"Failed to fetch URL: {e}"
