"""Daily data fetch pipeline — orchestrates all API calls and caching."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_config
from src.data.cache import DataCache
from src.data.feishu_client import FeishuClient
from src.data.fred_client import FredClient
from src.data.stock_prices import StockPriceFetcher
from src.data.tavily_client import TavilyClient
from src.llm.deepseek_client import DeepSeekClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline(skip_llm: bool = False) -> dict:
    """
    Execute full daily data fetch:
    1. Load config from Feishu
    2. Fetch FRED metrics
    3. Fetch stock prices
    4. Fetch macro & stock news via Tavily
    5. LLM news summary (optional)
    6. Cache everything
    """
    config = get_config()
    cache = DataCache(config.cache_dir, config.timezone)
    errors: list[str] = []

    # --- Feishu config ---
    feishu = FeishuClient(config.feishu)
    stocks_config: list = []
    metrics_config: list = []

    try:
        stocks_config = feishu.get_stocks()
        cache.save("stocks_config", stocks_config)
    except Exception as e:
        msg = f"Feishu stocks: {e}"
        logger.error(msg)
        errors.append(msg)
        stocks_config = cache.load("stocks_config", [])

    try:
        metrics_config = feishu.get_metrics_config()
        cache.save("metrics_config", metrics_config)
    except Exception as e:
        msg = f"Feishu metrics: {e}"
        logger.error(msg)
        errors.append(msg)
        metrics_config = cache.load("metrics_config", [])

    # --- FRED metrics ---
    fred = FredClient(config.fred)
    metrics: list = []
    try:
        metrics = fred.fetch_metrics(metrics_config)
        cache.save("metrics", metrics)
        logger.info("Cached %d metrics", len(metrics))
    except Exception as e:
        msg = f"FRED: {e}"
        logger.error(msg)
        errors.append(msg)
        metrics = cache.load("metrics", [])

    # --- Stock prices ---
    price_fetcher = StockPriceFetcher()
    stocks: list = []
    try:
        stocks = price_fetcher.fetch_prices(stocks_config)
        cache.save("stocks", stocks)
        logger.info("Cached %d stock prices", len(stocks))
    except Exception as e:
        msg = f"Stock prices: {e}"
        logger.error(msg)
        errors.append(msg)
        stocks = cache.load("stocks", [])

    # --- News ---
    tavily = TavilyClient(config.tavily)
    macro_news: list = []
    stock_news: list = []

    try:
        macro_news = tavily.fetch_macro_news()
        cache.save("macro_news", macro_news)
        logger.info("Cached %d macro news articles", len(macro_news))
    except Exception as e:
        msg = f"Macro news: {e}"
        logger.error(msg)
        errors.append(msg)
        macro_news = cache.load("macro_news", [])

    try:
        tickers = [s["ticker"] for s in stocks_config]
        stock_news = tavily.fetch_stock_news(tickers)
        cache.save("stock_news", stock_news)
        logger.info("Cached %d stock news articles", len(stock_news))
    except Exception as e:
        msg = f"Stock news: {e}"
        logger.error(msg)
        errors.append(msg)
        stock_news = cache.load("stock_news", [])

    # --- LLM Summary ---
    summary = ""
    if not skip_llm:
        llm = DeepSeekClient(config.deepseek)
        if llm.is_configured:
            try:
                summary = llm.summarize_news(macro_news, stock_news, metrics, stocks)
                cache.save("news_summary", {"summary": summary, "generated": True})
                logger.info("News summary generated")
            except Exception as e:
                msg = f"LLM summary: {e}"
                logger.error(msg)
                errors.append(msg)
                cache.save(
                    "news_summary",
                    {"summary": "", "generated": False, "error": str(e)},
                )
        else:
            logger.warning("DeepSeek API key not set — skipping news summary")
            cache.save(
                "news_summary",
                {"summary": "", "generated": False, "reason": "API key not configured"},
            )
    else:
        logger.info("Skipping LLM summary (--skip-llm)")

    status = "success" if not errors else "partial" if metrics or stocks else "failed"
    cache.update_metadata(status=status, errors=errors)

    return {
        "status": status,
        "errors": errors,
        "metrics_count": len(metrics),
        "stocks_count": len(stocks),
        "macro_news_count": len(macro_news),
        "stock_news_count": len(stock_news),
        "summary_generated": bool(summary),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Investboard daily data pipeline")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM news summary")
    args = parser.parse_args()

    result = run_pipeline(skip_llm=args.skip_llm)
    print(f"Pipeline finished: {result}")
