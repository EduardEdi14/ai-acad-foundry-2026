"""A deliberately plain web scraper — the "do it yourself" comparison.

This module exists to be *honest about the work*. Fetching a page and extracting
its readable text looks like five lines until you meet reality: JavaScript-rendered
pages, cookie walls, bot protection, rate limits, encodings, boilerplate
navigation, robots.txt, and the fact that every site's HTML is different and
changes without notice.

We implement the naive version properly (standard library HTML parsing, no extra
dependency), and we report what it *could not* do. That report is the teaching
material: it is the argument for using a managed grounding tool instead of
maintaining scrapers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}
BOILERPLATE_TAGS = {"nav", "header", "footer", "aside", "form"}
USER_AGENT = "LibraAcademyTeachingBot/1.0 (+course exercise)"


class _TextExtractor(HTMLParser):
    """Collect visible text; note structural signals that reveal the hard cases."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.title: str | None = None
        self._skip_depth = 0
        self._boilerplate_depth = 0
        self._in_title = False
        self.script_count = 0
        self.link_count = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            if tag == "script":
                self.script_count += 1
        elif tag in BOILERPLATE_TAGS:
            self._boilerplate_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            self.link_count += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in BOILERPLATE_TAGS and self._boilerplate_depth:
            self._boilerplate_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip() or None
        if self._skip_depth or self._boilerplate_depth:
            return
        text = data.strip()
        if text:
            self.chunks.append(text)


@dataclass
class ScrapeResult:
    url: str
    status_code: int
    title: str | None
    text: str
    chars: int
    approx_tokens: int
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def scrape(url: str, timeout: float = 10.0, max_chars: int = 20000) -> ScrapeResult:
    if not urlparse(url).scheme:
        url = "https://" + url

    with httpx.Client(follow_redirects=True, timeout=timeout,
                      headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)

    warnings: list[str] = []
    content_type = response.headers.get("content-type", "")

    if response.status_code == 403:
        warnings.append(
            "403 Forbidden — the site refused an automated client. Bot protection "
            "(Cloudflare, Akamai) is the single most common wall for home-grown scrapers."
        )
    elif response.status_code == 429:
        warnings.append("429 Too Many Requests — you are being rate-limited.")
    elif response.status_code >= 400:
        warnings.append(f"HTTP {response.status_code} — nothing to extract.")

    if "html" not in content_type:
        warnings.append(f"Content-Type is '{content_type or 'unknown'}', not HTML — "
                        "a real pipeline needs a parser per format (PDF, DOCX, XML…).")

    parser = _TextExtractor()
    try:
        parser.feed(response.text)
    except Exception as e:                                   # malformed markup happens
        warnings.append(f"HTML parsing failed part-way: {e}")

    text = re.sub(r"\n{3,}", "\n\n", "\n".join(parser.chunks)).strip()

    if len(text) < 200 and parser.script_count > 3:
        warnings.append(
            f"Very little text ({len(text)} chars) but {parser.script_count} script tags — "
            "this page is probably rendered by JavaScript. A plain HTTP fetch cannot see "
            "that content; you would need a headless browser."
        )
    if re.search(r"cookie|consent|gdpr", text[:800], re.I):
        warnings.append("A cookie/consent banner appears in the extracted text — "
                        "boilerplate removal is site-specific work.")
    if len(text) > max_chars:
        text = text[:max_chars]
        warnings.append(f"Truncated to {max_chars} characters.")

    return ScrapeResult(
        url=str(response.url),
        status_code=response.status_code,
        title=parser.title,
        text=text,
        chars=len(text),
        approx_tokens=max(1, round(len(text) / 4)),
        warnings=warnings,
        stats={
            "html_bytes": len(response.content),
            "text_bytes": len(text),
            "signal_ratio": round(len(text) / max(1, len(response.content)), 4),
            "script_tags": parser.script_count,
            "links": parser.link_count,
            "final_url": str(response.url),
            "redirected": str(response.url) != url,
        },
    )
