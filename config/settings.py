"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_env(key: str, default: str = "") -> str:
    """Read config from env vars, falling back to Streamlit secrets."""
    val = os.getenv(key)
    if val:
        return val.strip()
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key]).strip()
        # Support [api_keys] nested sections in secrets.toml
        for section in st.secrets.values():
            if isinstance(section, dict) and key in section:
                return str(section[key]).strip()
    except Exception:
        pass
    return default


DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
PROMPTS_DIR = PROJECT_ROOT / "src" / "prompts"


@dataclass
class FeishuConfig:
    app_id: str = field(default_factory=lambda: _get_env("FEISHU_APP_ID"))
    app_secret: str = field(default_factory=lambda: _get_env("FEISHU_APP_SECRET"))
    app_token: str = field(default_factory=lambda: _get_env("FEISHU_APP_TOKEN"))
    stock_table_id: str = field(
        default_factory=lambda: _get_env("FEISHU_STOCK_TABLE_ID", "tblM0Zf6o3P07Eqm")
    )
    metric_table_id: str = field(
        default_factory=lambda: _get_env("FEISHU_METRIC_TABLE_ID", "tbl212wNdrhVC1Ig")
    )


@dataclass
class FredConfig:
    api_key: str = field(default_factory=lambda: _get_env("FRED_API_KEY"))
    base_url: str = "https://api.stlouisfed.org/fred/series/observations"


@dataclass
class TavilyConfig:
    api_key: str = field(default_factory=lambda: _get_env("TAVILY_API_KEY"))
    base_url: str = "https://api.tavily.com/search"


@dataclass
class DeepSeekConfig:
    api_key: str = field(default_factory=lambda: _get_env("DEEPSEEK_API_KEY"))
    base_url: str = field(
        default_factory=lambda: _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    model: str = field(default_factory=lambda: _get_env("DEEPSEEK_MODEL", "deepseek-chat"))


@dataclass
class AppConfig:
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    fred: FredConfig = field(default_factory=FredConfig)
    tavily: TavilyConfig = field(default_factory=TavilyConfig)
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    cache_dir: Path = CACHE_DIR
    timezone: str = field(default_factory=lambda: _get_env("TZ", "Asia/Shanghai"))


def get_config() -> AppConfig:
    """Return singleton application config."""
    return AppConfig()
