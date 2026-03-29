"""AIRA module: agents/market_gpt/article_fetcher.py"""

import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ET_MARKETS_URL = "https://economictimes.indiatimes.com/markets/stocks/news"

_FALLBACK_HEADLINES = [
    {
        "title": "Nifty closes higher on banking support",
        "url": "https://economictimes.indiatimes.com/markets/stocks/news/sample-nifty-banking-support",
        "description": "Benchmark indices gained as banking and large-cap IT stocks supported sentiment.",
        "source": "sample_data",
    },
    {
        "title": "FII flows turn positive in late session",
        "url": "https://economictimes.indiatimes.com/markets/stocks/news/sample-fii-flows-positive",
        "description": "Foreign investors were net buyers as risk appetite improved in the second half.",
        "source": "sample_data",
    },
    {
        "title": "Midcap rally cools after sharp weekly gains",
        "url": "https://economictimes.indiatimes.com/markets/stocks/news/sample-midcap-rally-cools",
        "description": "Profit booking emerged in select midcaps after a strong run-up.",
        "source": "sample_data",
    },
]


async def fetch_et_markets_headlines() -> list[dict[str, str]]:
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = await client.get(ET_MARKETS_URL)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        candidates: list[dict[str, str]] = []
        for anchor in soup.select("a[href]"):
            href = str(anchor.get("href") or "").strip()
            title = " ".join(anchor.get_text(" ", strip=True).split())
            if not href or not title:
                continue
            if "/markets/stocks/news/" not in href:
                continue
            if len(title) < 25:
                continue

            full_url = href if href.startswith("http") else urljoin("https://economictimes.indiatimes.com", href)
            if any(item["url"] == full_url for item in candidates):
                continue

            description = ""
            card = anchor.find_parent(["div", "li", "article"])
            if card is not None:
                for tag in card.find_all(["p", "span"], limit=3):
                    text = " ".join(tag.get_text(" ", strip=True).split())
                    if len(text) > 40 and text != title:
                        description = text
                        break

            candidates.append(
                {
                    "title": title,
                    "url": full_url,
                    "description": description or "No summary available.",
                    "source": "ET Markets",
                }
            )
            if len(candidates) >= 10:
                break

        if not candidates:
            logger.warning("ET Markets parsing yielded no headlines, using fallback data")
            return _FALLBACK_HEADLINES

        return candidates
    except Exception as exc:
        logger.exception("Failed to fetch ET Markets headlines error=%s", exc)
        return _FALLBACK_HEADLINES


async def fetch_article_content(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        for selector in ["nav", "header", "footer", "aside", ".ad", ".ads", "script", "style"]:
            for element in soup.select(selector):
                element.decompose()

        text_blocks: list[str] = []
        article_container = soup.find("article")
        if article_container is not None:
            paragraphs = article_container.find_all("p")
        else:
            paragraphs = soup.find_all("p")

        for paragraph in paragraphs:
            text = " ".join(paragraph.get_text(" ", strip=True).split())
            if len(text) >= 40:
                text_blocks.append(text)

        content = "\n".join(text_blocks)
        if not content:
            content = "Unable to extract detailed article content."

        return content[:2000]
    except Exception as exc:
        logger.exception("Failed to fetch article content url=%s error=%s", url, exc)
        return "Article content unavailable due to fetch error."


def _keyword_match_score(query: str, text: str) -> int:
    query_tokens = [token.lower() for token in query.split() if len(token.strip()) > 2]
    haystack = text.lower()
    return sum(1 for token in query_tokens if token in haystack)


async def build_news_context(query: str) -> str:
    headlines = await fetch_et_markets_headlines()
    query_text = (query or "").strip()

    if query_text:
        ranked = sorted(
            headlines,
            key=lambda item: _keyword_match_score(query_text, f"{item.get('title', '')} {item.get('description', '')}"),
            reverse=True,
        )
        relevant = [item for item in ranked if _keyword_match_score(query_text, f"{item.get('title', '')} {item.get('description', '')}") > 0]
    else:
        relevant = headlines

    selected = (relevant or headlines)[:3]
    if not selected:
        return "No recent market news context available."

    contents = await asyncio.gather(*[fetch_article_content(item["url"]) for item in selected])

    parts = []
    for article, content in zip(selected, contents):
        parts.append(
            "\n".join(
                [
                    f"Title: {article.get('title')}",
                    f"Source: {article.get('source')}",
                    f"URL: {article.get('url')}",
                    f"Summary: {article.get('description')}",
                    f"Content Excerpt: {content}",
                ]
            )
        )

    return "\n\n".join(parts)


async def search_market_news(query: str, symbols: list) -> str:
    symbols_upper = [str(symbol).upper().strip() for symbol in (symbols or []) if str(symbol).strip()]
    merged_query = " ".join([query or "", *symbols_upper]).strip()

    headlines = await fetch_et_markets_headlines()

    relevant: list[dict[str, str]] = []
    for item in headlines:
        text = f"{item.get('title', '')} {item.get('description', '')}".upper()
        if symbols_upper and any(symbol in text for symbol in symbols_upper):
            relevant.append(item)
            continue
        if merged_query and _keyword_match_score(merged_query, text) > 0:
            relevant.append(item)

    selected = relevant[:3] if relevant else headlines[:3]
    if not selected:
        return "No market news available right now."

    contents = await asyncio.gather(*[fetch_article_content(item["url"]) for item in selected])

    lines = ["Relevant market news:"]
    for article, content in zip(selected, contents):
        lines.append(f"- {article.get('title')} ({article.get('source')})")
        lines.append(f"  URL: {article.get('url')}")
        lines.append(f"  Excerpt: {content[:500]}")

    return "\n".join(lines)
