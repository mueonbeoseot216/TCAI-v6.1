"""
TCAI Gateway — web search engine (Bing).

Abstraction over search backends. Default: Bing (no API key required in China).
Extensible to other search engines via the same interface.
"""
from __future__ import annotations

import re
import html as html_module
from typing import NamedTuple

from ..http_client import http_client, HttpResponse
from ..config import config
from .. import logging_setup

logger = logging_setup.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════════════


class SearchResult(NamedTuple):
    """A single search result from any engine."""

    title: str
    url: str
    snippet: str


# ═══════════════════════════════════════════════════════════════════════
# Bing HTML parsing
# ═══════════════════════════════════════════════════════════════════════

_ALGO_PATTERN: re.Pattern[str] = re.compile(
    r'<li\s+class="b_algo"[^>]*>(.*?)</li>', re.DOTALL
)

_TITLE_RE: re.Pattern[str] = re.compile(
    r'<h2[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.DOTALL
)

_CAPTION_RE: re.Pattern[str] = re.compile(
    r'<div\s+class="(?:b_caption|b_snippet)[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)

_TEXT_LINES_RE: re.Pattern[str] = re.compile(r'>([^<]{10,400})<')

_FALLBACK_LINK_RE: re.Pattern[str] = re.compile(
    r'<a[^>]*href="(https?://[^"]+)"[^>]*>\s*(?:<h\d[^>]*>)?\s*([^<]{5,100})\s*(?:</h\d>)?\s*</a>',
    re.DOTALL,
)


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_bing_html(html_text: str, count: int) -> list[SearchResult]:
    """Parse Bing HTML search results page."""
    results: list[SearchResult] = []
    blocks = _ALGO_PATTERN.findall(html_text)

    for block in blocks:
        if len(results) >= count:
            break

        title_match = _TITLE_RE.search(block)
        if not title_match:
            continue

        url = title_match.group(1).strip()
        title = _strip_tags(title_match.group(2))

        if not url.startswith(("http://", "https://")):
            continue

        # Extract snippet
        snippet = ""
        caption_match = _CAPTION_RE.search(block)
        if caption_match:
            snippet = _strip_tags(caption_match.group(1))
        else:
            text_lines = _TEXT_LINES_RE.findall(block)
            for line in text_lines:
                clean = _strip_tags(line)
                if clean in (title, url) or clean.startswith("http"):
                    continue
                if any(sep in clean for sep in ("›", "»", " · ")):
                    continue
                if len(clean) > 15:
                    snippet = clean
                    break

        # Truncate snippet at 300 chars
        if snippet and len(snippet) > 300:
            parts = snippet[:300].rsplit("。", 1)
            snippet = (parts[0] + "。") if len(parts) > 1 else snippet[:297] + "..."

        if not snippet:
            snippet = "(No snippet)"

        results.append(SearchResult(title=title, url=url, snippet=snippet))

    # Fallback parsing if b_algo not found
    if not results:
        results = _parse_bing_fallback(html_text, count)

    return results


def _parse_bing_fallback(html_text: str, count: int) -> list[SearchResult]:
    """Loose fallback parsing for mobile/old Bing formats."""
    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for url, title in _FALLBACK_LINK_RE.findall(html_text):
        if len(results) >= count:
            break
        url = url.strip()
        title = _strip_tags(title)
        if url in seen_urls or "bing.com" in url:
            continue
        if len(title) < 5:
            continue
        seen_urls.add(url)
        results.append(SearchResult(title=title, url=url, snippet="(No snippet)"))

    return results


# ═══════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════


def search(query: str, count: int = 5) -> list[SearchResult]:
    """Search the web using Bing and return structured results.

    Args:
        query: Search query string.
        count: Maximum results to return (1-10).

    Returns:
        List of SearchResult named tuples. Empty list on failure.
    """
    if not query or not query.strip():
        return []

    count = min(max(count, 1), config.web_max_results)

    params = {
        "q": query.strip(),
        "count": str(min(count, 15)),
        "setlang": "zh-Hans",
    }

    try:
        response = http_client.get(
            config.bing_search_url,
            timeout=config.web_search_timeout,
            params=params,
        )
    except (OSError, ValueError) as e:
        logger.warning(f"Bing search failed: {e}")
        return []

    if not response.ok:
        logger.warning(f"Bing returned HTTP {response.status_code}")
        return []

    return _parse_bing_html(response.text, count)
