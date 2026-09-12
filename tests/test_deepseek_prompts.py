"""Tests for prompt loading."""

from src.llm.deepseek_client import DeepSeekClient
from config.settings import DeepSeekConfig


def test_load_prompt_keeps_markdown_headings():
    client = DeepSeekClient(DeepSeekConfig())
    system = client.load_prompt("news_summary_system.txt")
    assert "Role" in system or "宏观" in system or len(system) > 20

    user = client.load_prompt("news_summary_user.txt")
    assert "{{CONTEXT}}" in user or "Context" in user
