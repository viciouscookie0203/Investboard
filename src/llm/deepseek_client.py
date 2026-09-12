"""DeepSeek LLM client (OpenAI-compatible API)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from openai import OpenAI

from config.settings import DeepSeekConfig, PROMPTS_DIR

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Chat and summarization via DeepSeek API."""

    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self._client: OpenAI | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def _get_client(self) -> OpenAI:
        if not self.config.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在 .env 或 Streamlit Secrets 中填写")
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    def load_prompt(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        if not path.exists():
            return ""
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Skip template placeholder hints only (not markdown headings like "# Role")
            if stripped.startswith("#") and any(
                hint in stripped
                for hint in ("在此填写", "示例", "Example", "Copy to", "占位符", "{{CONTEXT}}")
            ):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def summarize_news(
        self,
        macro_news: list[dict[str, Any]],
        stock_news: list[dict[str, Any]],
        metrics: list[dict[str, Any]] | None = None,
        stocks: list[dict[str, Any]] | None = None,
    ) -> str:
        """Summarize all news with user-defined prompt template."""
        system_prompt = self.load_prompt("news_summary_system.txt")
        user_template = self.load_prompt("news_summary_user.txt")

        if not system_prompt:
            system_prompt = (
                "你是一位专业的宏观与权益市场分析师。"
                "请根据提供的新闻和数据，总结今日需要关注的核心要点。"
            )

        context = self._build_context(macro_news, stock_news, metrics, stocks)

        if user_template:
            user_message = user_template.replace("{{CONTEXT}}", context)
        else:
            user_message = (
                "请根据以下看板数据与新闻，总结目前应该注意的要点：\n\n"
                f"{context}"
            )

        return self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        )

    def ask_about_dashboard(
        self,
        question: str,
        dashboard_context: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Interactive Q&A based on current dashboard state."""
        system_prompt = self.load_prompt("chat_system.txt")
        if not system_prompt:
            system_prompt = (
                "你是 Investboard 投资看板助手。"
                "基于提供的看板数据回答用户问题，给出清晰、可执行的分析。"
                "如果数据不足以回答，请明确说明。"
            )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if chat_history:
            messages.extend(chat_history)

        messages.append(
            {
                "role": "user",
                "content": f"【看板数据】\n{dashboard_context}\n\n【用户问题】\n{question}",
            }
        )

        return self.chat(messages)

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _build_context(
        macro_news: list[dict[str, Any]],
        stock_news: list[dict[str, Any]],
        metrics: list[dict[str, Any]] | None,
        stocks: list[dict[str, Any]] | None,
    ) -> str:
        parts: list[str] = []

        if metrics:
            parts.append("## 宏观指标")
            for m in metrics:
                val = m.get("value")
                parts.append(
                    f"- {m.get('name')}: {val} {m.get('unit', '')} "
                    f"[{m.get('status_label', '')}] (截至 {m.get('date', 'N/A')})"
                )

        if stocks:
            parts.append("\n## 股票行情")
            for s in stocks:
                parts.append(
                    f"- {s.get('ticker')} {s.get('name')}: "
                    f"{s.get('price')} ({s.get('change_pct', 0):+.2f}%)"
                )

        if macro_news:
            parts.append("\n## 宏观新闻")
            for i, n in enumerate(macro_news[:15], 1):
                parts.append(f"{i}. {n.get('title')} — {n.get('url')}")

        if stock_news:
            parts.append("\n## 个股新闻")
            for i, n in enumerate(stock_news[:20], 1):
                ticker = n.get("ticker", "")
                parts.append(f"{i}. [{ticker}] {n.get('title')} — {n.get('url')}")

        return "\n".join(parts)
