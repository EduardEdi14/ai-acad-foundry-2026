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

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from ..config import settings

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}
BOILERPLATE_TAGS = {"nav", "header", "footer", "aside", "form"}
USER_AGENT = "LibraAcademyTeachingBot/1.0 (+course exercise)"

# Search engines serve an anti-bot challenge to clients that identify as bots, so
# the honest UA above returns no results at all. A browser-shaped one works. That
# tension — declare yourself and be blocked, or blend in and be tolerated — has no
# clean answer, and it is a large part of why production systems buy a search API
# instead of scraping one. Do not carry this pattern into anything commercial
# without reading the target's terms of use.
SEARCH_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class WebSearchBlocked(Exception):
    """The engine returned a challenge page rather than results."""


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
class SearchHitWeb:
    rank: int
    title: str
    url: str
    snippet: str


def search(query: str, max_results: int = 5, timeout: float = 20.0) -> tuple[list[SearchHitWeb], str]:
    """Search the web through whichever provider is configured.

    Returns the hits and the provider that answered, because *which* one answered
    is the lesson. Order of preference:

      brave / serper   a real search API — a documented contract, a key, a quota,
                       and results that arrive every time. Both have free tiers.
      duckduckgo       scraping the HTML endpoint. No key, no contract, and it
                       serves a bot challenge under any real load — including a
                       classroom running it at the same moment.

    In Foundry the managed equivalent is *Grounding with Bing Search*, an agent
    tool. It needs a Bing-eligible subscription (`SkuNotEligible` otherwise), which
    is why this module exists at all.
    """
    provider = (settings.search_provider or "auto").lower()
    key = settings.search_api_key

    if provider in ("brave", "auto") and key and provider != "serper":
        try:
            return _search_brave(query, max_results, key, timeout), "brave-search-api (managed)"
        except Exception:
            if provider == "brave":
                raise
    if provider in ("serper", "auto") and key:
        try:
            return _search_serper(query, max_results, key, timeout), "serper.dev (managed)"
        except Exception:
            if provider == "serper":
                raise
    return _search_duckduckgo(query, max_results, timeout), "duckduckgo-html (keyless, unmanaged)"


def _search_brave(query: str, max_results: int, key: str, timeout: float) -> list[SearchHitWeb]:
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": max_results},
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    results = response.json().get("web", {}).get("results", [])[:max_results]
    return [
        SearchHitWeb(rank=i, title=r.get("title", ""), url=r.get("url", ""),
                     snippet=_strip_tags(r.get("description", "")))
        for i, r in enumerate(results, start=1)
    ]


def _search_serper(query: str, max_results: int, key: str, timeout: float) -> list[SearchHitWeb]:
    response = httpx.post(
        "https://google.serper.dev/search",
        json={"q": query, "num": max_results},
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    results = response.json().get("organic", [])[:max_results]
    return [
        SearchHitWeb(rank=i, title=r.get("title", ""), url=r.get("link", ""),
                     snippet=r.get("snippet", ""))
        for i, r in enumerate(results, start=1)
    ]


def _search_duckduckgo(query: str, max_results: int = 5, timeout: float = 20.0) -> list[SearchHitWeb]:
    """Search the open web without an API key.

    We use DuckDuckGo's HTML endpoint and parse the result list. This is honest
    about what it is — screen scraping, subject to every fragility documented in
    `scrape()` — and it exists so the "search the web" capability can be exercised
    on any subscription.

    The managed alternative is *Grounding with Bing Search*, a Foundry agent tool.
    It is better in every way that matters (stable contract, no parsing, terms of
    use sorted) and requires a subscription eligible for the Bing SKU — which many,
    including trials, are not. That trade-off is the lesson.
    """
    response = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={"User-Agent": SEARCH_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()

    # 202 with a short body is the anti-bot challenge, not a result page.
    if response.status_code == 202 or "result__a" not in response.text:
        raise WebSearchBlocked(
            "The search engine served a bot challenge instead of results "
            f"(HTTP {response.status_code}, {len(response.text)} bytes). This is the "
            "normal failure mode of do-it-yourself web search: the contract is HTML "
            "that can change or be withheld at any moment. A managed grounding tool "
            "returns a supported API response instead."
        )

    hits: list[SearchHitWeb] = []
    blocks = re.split(r'class="result__body"', response.text)[1:]
    for i, block in enumerate(blocks[: max_results * 2], start=1):
        link = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        snippet = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.S)
        url = _clean_url(html.unescape(link.group(1)))
        if not url:
            continue
        hits.append(SearchHitWeb(
            rank=len(hits) + 1,
            title=_strip_tags(link.group(2)),
            url=url,
            snippet=_strip_tags(snippet.group(1)) if snippet else "",
        ))
        if len(hits) >= max_results:
            break
    return hits


def _strip_tags(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _clean_url(href: str) -> str:
    """DuckDuckGo wraps results in a redirect; unwrap it to the real destination."""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target)
    return href


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
