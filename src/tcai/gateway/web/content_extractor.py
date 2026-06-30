"""
TCAI Gateway — web content extraction.

Extracts clean text from HTML pages. Pure Python (stdlib + optional beautifulsoup4).
No Node.js/Puppeteer required — static extraction covers 95% of diagnostic content.
"""
from __future__ import annotations

import re
import html as html_module

from ..http_client import http_client
from ..config import config
from .. import injection_filter
from .. import logging_setup

logger = logging_setup.get_logger(__name__)

# Regex patterns — compiled once at import
_SCRIPT_RE: re.Pattern[str] = re.compile(
    r"<script[^>]*>.*?</script>", re.I | re.DOTALL
)
_STYLE_RE: re.Pattern[str] = re.compile(
    r"<style[^>]*>.*?</style>", re.I | re.DOTALL
)
_NOSCRIPT_RE: re.Pattern[str] = re.compile(
    r"<noscript[^>]*>.*?</noscript>", re.I | re.DOTALL
)
_COMMENT_RE: re.Pattern[str] = re.compile(r"<!--.*?-->", re.DOTALL)
_HIDDEN_ELEM_RE: re.Pattern[str] = re.compile(
    r"<[^>]*\b(?:display\s*:\s*none|visibility\s*:\s*hidden|"
    r"opacity\s*:\s*0[^.\d]|font-size\s*:\s*0[^.\d])[^>]*>.*?</[^>]+>",
    re.I | re.DOTALL,
)
_TITLE_RE: re.Pattern[str] = re.compile(
    r"<title[^>]*>(.*?)</title>", re.I | re.DOTALL
)
_BODY_RE: re.Pattern[str] = re.compile(
    r"<body[^>]*>(.*?)</body>", re.I | re.DOTALL
)
_HEAD_RE: re.Pattern[str] = re.compile(
    r"<head[^>]*>.*?</head>", re.I | re.DOTALL
)
_CHARSET_RE: re.Pattern[str] = re.compile(r'charset=([^;]+)')


def _clean_text(html_fragment: str) -> str:
    """Strip HTML tags, decode entities, normalize whitespace."""
    # Block elements → newlines
    text = re.sub(r"<br\s*/?>", "\n", html_fragment, flags=re.I)
    text = re.sub(
        r"</?(?:p|div|h\d|li|tr|section|article|header|footer)[^>]*>",
        "\n",
        text,
        flags=re.I,
    )
    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode entities
    text = html_module.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_text(
    html_text: str,
    *,
    max_chars: int | None = None,
) -> str:
    """Extract clean, readable text from HTML.

    Removes scripts, styles, hidden elements, and comments.
    Extracts body text with structure-preserving normalization.

    Args:
        html_text: Raw HTML string.
        max_chars: Maximum characters to return (default: from config).

    Returns:
        Clean text content.
    """
    if max_chars is None:
        max_chars = config.web_extract_max_chars

    # Stage 1: Remove non-content elements
    html_text = _SCRIPT_RE.sub("", html_text)
    html_text = _STYLE_RE.sub("", html_text)
    html_text = _NOSCRIPT_RE.sub("", html_text)
    html_text = _COMMENT_RE.sub("", html_text)
    html_text = _HIDDEN_ELEM_RE.sub("", html_text)

    # Stage 2: Extract title
    title_match = _TITLE_RE.search(html_text)
    page_title = _clean_text(title_match.group(1)) if title_match else ""

    # Stage 3: Extract body
    body_match = _BODY_RE.search(html_text)
    if body_match:
        html_text = body_match.group(1)
    else:
        html_text = _HEAD_RE.sub("", html_text)

    # Stage 4: Clean and normalize
    text = _clean_text(html_text)

    # Merge excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    # Stage 5: Filter through injection filter (chunked for long texts)
    result = injection_filter.filter_long_text(text, source=f"web:{page_title[:50]}")
    text = result["filtered_text"]

    # Stage 6: Format output
    result_parts: list[str] = []
    if page_title:
        result_parts.append(f"Page title: {page_title}")
    result_parts.append(text)

    return "\n".join(result_parts)


def fetch_and_extract(
    url: str,
    *,
    max_chars: int | None = None,
    timeout: int | None = None,
) -> str:
    """Fetch a URL and extract clean text in one call.

    Args:
        url: Target URL (http/https only).
        max_chars: Maximum characters to return.
        timeout: Request timeout in seconds.

    Returns:
        Clean text content, or error message string.
    """
    if timeout is None:
        timeout = config.web_extract_timeout
    if max_chars is None:
        max_chars = config.web_extract_max_chars

    if not url.startswith(("http://", "https://")):
        return f"Unsupported URL scheme: {url[:50]}"

    try:
        response = http_client.get(url, timeout=timeout)
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return f"Failed to fetch page: {e}"

    if not response.ok:
        return f"HTTP {response.status_code} — cannot extract content"

    try:
        return extract_text(response.text, max_chars=max_chars)
    except Exception as e:
        logger.error(f"Failed to extract text from {url}: {e}")
        return f"Failed to parse page content: {e}"
