"""Tavily API client for macro and stock news."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import TavilyConfig

logger = logging.getLogger(__name__)

MACRO_NEWS_QUERY = (
    "Global macro market comprehensive daily wrap report SP500 Nasdaq HangSeng "
    "volatility capital flows -individual -breaking "
    "Wall Street institutional fund flows large whale alerts AND "
    "macroeconomic earnings calendar expected this week"
)

STOCK_NEWS_QUERY_TEMPLATE = (
    "{ticker} (news OR earnings OR stock price movement OR 资金流动)"
)


class TavilyClient:
    """Search news via Tavily API."""

    def __init__(self, config: TavilyConfig):
        self.config = config

    def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        topic: str = "news",
    ) -> list[dict[str, Any]]:
        if not self.config.api_key:
            logger.warning("Tavily API key not configured")
            return []

        payload = {
            "api_key": self.config.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "topic": topic,
            "include_answer": False,
            "include_raw_content": False,
        }

        resp = requests.post(self.config.base_url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("results", []):
            articles.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                    "published_date": item.get("published_date", ""),
                }
            )
        return articles

    def fetch_macro_news(self, max_results: int = 15) -> list[dict[str, Any]]:
        logger.info("Fetching macro news from Tavily")
        articles = self.search(MACRO_NEWS_QUERY, max_results=max_results)
        for a in articles:
            a["category"] = "macro"
        return articles

    def fetch_stock_news(
        self, tickers: list[str], max_per_stock: int = 5
    ) -> list[dict[str, Any]]:
        """Fetch news for each ticker in the watchlist."""
        all_articles: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for ticker in tickers:
            query = STOCK_NEWS_QUERY_TEMPLATE.format(ticker=ticker)
            try:
                articles = self.search(query, max_results=max_per_stock)
                for a in articles:
                    url = a.get("url", "")
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)
                    a["category"] = "stock"
                    a["ticker"] = ticker
                    all_articles.append(a)
            except Exception as e:
                logger.error("Failed to fetch news for %s: %s", ticker, e)

        logger.info("Fetched %d stock news articles", len(all_articles))
        return all_articles
