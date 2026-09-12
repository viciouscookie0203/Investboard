"""
Investboard — 宏观投资数据看板
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_config
from src.data.cache import DataCache
from src.data.pipeline import run_pipeline
from src.llm.deepseek_client import DeepSeekClient
from src.visualization.gauges import render_gauge

st.set_page_config(
    page_title="Investboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAV_ITEMS = {
    "market": {"label": "市场总览", "icon": "📊"},
    "news": {"label": "新闻速递", "icon": "📰"},
}

CATEGORY_ORDER = ["宏观流动性", "跨资产波动", "信用与流动性", "避险对冲"]


def inject_css():
    st.markdown(
        """
<style>
    .block-container { padding-top: 0.75rem; padding-bottom: 4rem; max-width: 100%; }
    [data-testid="stSidebar"] { background: #0b1220; }
    [data-testid="stSidebar"] .nav-btn button {
        width: 100%;
        text-align: left;
        border-radius: 10px;
        margin-bottom: 6px;
        border: 1px solid #334155;
        background: #1e293b;
        color: #e2e8f0;
        font-size: 0.88rem;
        padding: 0.45rem 0.65rem;
    }
    [data-testid="stSidebar"] .nav-btn button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        border-color: #3b82f6;
        color: #fff;
    }
    h1 { font-size: 1.35rem !important; margin-bottom: 0.15rem !important; }
    h2, h3 { font-size: 0.95rem !important; margin: 0.35rem 0 !important; }
    p, li, span, label { font-size: 0.82rem; }
    .meta-line { color: #94a3b8; font-size: 0.72rem; margin-bottom: 0.35rem; }
    .news-card {
        background: #1e293b;
        border-left: 3px solid #3b82f6;
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 6px;
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .news-card a { color: #60a5fa; text-decoration: none; }
    .summary-box {
        background: #172554;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 0.8rem;
        line-height: 1.45;
        margin-bottom: 0.5rem;
    }
    .stock-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
    .stock-table th, .stock-table td {
        padding: 6px 8px;
        border-bottom: 1px solid #334155;
        text-align: right;
    }
    .stock-table th:first-child, .stock-table td:first-child { text-align: left; }
    .stock-table th { color: #94a3b8; font-weight: 600; }
    .up { color: #ef4444; }
    .down { color: #22c55e; }
    .err-box {
        background: #451a1a;
        border: 1px solid #991b1b;
        color: #fecaca;
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 0.75rem;
        margin-bottom: 0.5rem;
    }
    div.st-key-chat_fab {
        position: fixed !important;
        bottom: 14px !important;
        right: 14px !important;
        z-index: 9999 !important;
        width: auto !important;
    }
    div.st-key-chat_fab button {
        border-radius: 999px !important;
        min-width: 52px !important;
        min-height: 52px !important;
        font-size: 1.25rem !important;
        box-shadow: 0 8px 24px rgba(37, 99, 235, 0.45);
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        border: none !important;
        color: white !important;
    }
    @media (max-width: 768px) {
        .block-container { padding-left: 0.75rem; padding-right: 0.75rem; }
        h1 { font-size: 1.15rem !important; }
    }
</style>
""",
        unsafe_allow_html=True,
    )


def load_cached_data() -> dict:
    config = get_config()
    cache = DataCache(config.cache_dir, config.timezone)
    return {
        "metrics": cache.load("metrics", []),
        "stocks": cache.load("stocks", []),
        "macro_news": cache.load("macro_news", []),
        "stock_news": cache.load("stock_news", []),
        "news_summary": cache.load("news_summary", {}),
        "metadata": cache.load("metadata", {}),
        "last_updated": cache.get_last_updated(),
    }


def _friendly_errors(errors: list[str]) -> list[str]:
    out: list[str] = []
    for err in errors:
        if "402" in err or "Insufficient Balance" in err:
            out.append("DeepSeek 余额不足：行情与新闻已更新，AI 总结未生成")
        elif err.startswith("LLM summary:"):
            out.append(f"AI 总结失败：{err.replace('LLM summary: ', '', 1)[:120]}")
        else:
            out.append(err)
    return out


def _pipeline_status_label(meta: dict) -> str:
    status = meta.get("status", "unknown")
    errors = meta.get("errors") or []
    only_llm = errors and all("LLM summary" in e for e in errors)
    if status == "partial" and only_llm:
        return "数据已更新（AI 总结未生成）"
    return {"success": "正常", "partial": "部分成功", "failed": "失败"}.get(status, status)


def build_dashboard_context(data: dict) -> str:
    return DeepSeekClient(get_config().deepseek)._build_context(
        data.get("macro_news", []),
        data.get("stock_news", []),
        data.get("metrics", []),
        data.get("stocks", []),
    )


def render_sidebar_nav(data: dict) -> str:
    if "page" not in st.session_state:
        st.session_state.page = "market"

    with st.sidebar:
        st.markdown("### Investboard")
        st.caption("宏观 · 行情 · 新闻 · AI")

        for key, item in NAV_ITEMS.items():
            st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
            btn_type = "primary" if st.session_state.page == key else "secondary"
            if st.button(f"{item['icon']} {item['label']}", key=f"nav_{key}", type=btn_type):
                st.session_state.page = key
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()
        config = get_config()
        macro_n = len(data.get("macro_news", []))
        stock_n = len(data.get("stock_news", []))
        summary = data.get("news_summary", {})

        tavily_line = "Key 已配置" if config.tavily.api_key else "Key 未配置"
        if macro_n or stock_n:
            tavily_line += f" · 新闻 {macro_n + stock_n} 条"

        if not config.deepseek.api_key:
            llm_line = "Key 未配置"
        elif summary.get("summary"):
            llm_line = "Key 已配置 · 总结已生成"
        elif summary.get("error") and (
            "402" in str(summary["error"]) or "Insufficient Balance" in str(summary["error"])
        ):
            llm_line = "Key 已配置 · 余额不足"
        elif summary.get("error"):
            llm_line = "Key 已配置 · 总结失败"
        else:
            llm_line = "Key 已配置 · 待生成"

        st.caption("API 状态")
        st.markdown(f"- Tavily: {tavily_line}\n- DeepSeek: {llm_line}")
        st.caption(f"© {datetime.now().year}")

    return st.session_state.page


def render_header(data: dict):
    c1, c2 = st.columns([4, 1])
    with c1:
        st.title("Investboard")
        last = data.get("last_updated")
        meta = data.get("metadata", {})
        status_txt = _pipeline_status_label(meta)
        st.markdown(
            f'<div class="meta-line">更新: {last[:19].replace("T", " ") if last else "—"} · 状态: {status_txt}</div>',
            unsafe_allow_html=True,
        )
        for err in _friendly_errors(meta.get("errors", []))[:2]:
            st.markdown(f'<div class="err-box">{err}</div>', unsafe_allow_html=True)

    with c2:
        if st.button("🔄 刷新", use_container_width=True):
            with st.spinner("抓取中…"):
                result = run_pipeline(skip_llm=False)
            st.session_state["last_pipeline"] = result
            st.rerun()


def _ordered_categories(metrics: list) -> list[tuple[str, list]]:
    grouped: dict[str, list] = {}
    for m in metrics:
        cat = m.get("category") or "其他"
        grouped.setdefault(cat, []).append(m)

    ordered = []
    for cat in CATEGORY_ORDER:
        if cat in grouped:
            ordered.append((cat, grouped.pop(cat)))
    for cat, items in grouped.items():
        ordered.append((cat, items))
    return ordered


def render_market_page(data: dict):
    metrics = data.get("metrics", [])
    if not metrics:
        st.info("暂无指标数据，请点击刷新。")
    else:
        for cat, cat_metrics in _ordered_categories(metrics):
            st.markdown(f"**{cat}**")
            cols = st.columns(len(cat_metrics))
            for col, m in zip(cols, cat_metrics):
                with col:
                    fig = render_gauge(m)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown("**股票行情**")
    render_stocks(data)


def render_stocks(data: dict):
    stocks = data.get("stocks", [])
    if not stocks:
        st.info("暂无股票数据")
        return

    valid = [s for s in stocks if s.get("change_pct") is not None]
    if valid:
        fig = go.Figure(
            go.Bar(
                x=[s["ticker"] for s in valid],
                y=[s["change_pct"] for s in valid],
                marker_color=["#ef4444" if s["change_pct"] >= 0 else "#22c55e" for s in valid],
                text=[f"{s['change_pct']:+.1f}%" for s in valid],
                textposition="outside",
                textfont={"size": 9},
            )
        )
        fig.update_layout(
            height=160,
            margin=dict(l=8, r=8, t=8, b=8),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#cbd5e1", "size": 9},
            yaxis={"title": "", "gridcolor": "#334155", "zerolinecolor": "#475569"},
            xaxis={"title": "", "gridcolor": "#334155"},
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    rows = []
    for s in stocks:
        pct = s.get("change_pct")
        chg = s.get("change")
        if pct is None:
            arrow, cls, pct_txt, chg_txt = "—", "", "N/A", "N/A"
        elif pct >= 0:
            arrow, cls = "▲", "up"
            pct_txt, chg_txt = f"{pct:+.2f}%", f"{chg:+.2f}" if chg is not None else "—"
        else:
            arrow, cls = "▼", "down"
            pct_txt, chg_txt = f"{pct:+.2f}%", f"{chg:+.2f}" if chg is not None else "—"

        price = s.get("price")
        price_txt = f"{price:.2f}" if price is not None else "—"
        rows.append(
            f"<tr>"
            f"<td><b>{s.get('ticker', '')}</b></td>"
            f"<td>{price_txt}</td>"
            f"<td class='{cls}'>{arrow} {chg_txt}</td>"
            f"<td class='{cls}'>{arrow} {pct_txt}</td>"
            f"</tr>"
        )

    table_html = (
        "<table class='stock-table'>"
        "<thead><tr><th>代码</th><th>最新价</th><th>涨跌</th><th>涨跌幅</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_news_card(article: dict, show_ticker: bool = False):
    title = article.get("title", "无标题")
    url = article.get("url", "")
    content = article.get("content", "")
    ticker = article.get("ticker", "")
    prefix = f"[{ticker}] " if show_ticker and ticker else ""
    link = f'<a href="{url}" target="_blank">{prefix}{title}</a>' if url else f"{prefix}{title}"
    snippet = content[:120] + "…" if len(content) > 120 else content
    st.markdown(f'<div class="news-card">{link}<br><span style="color:#94a3b8">{snippet}</span></div>', unsafe_allow_html=True)


def render_news_page(data: dict):
    summary_data = data.get("news_summary", {})
    summary = summary_data.get("summary", "")

    macro_n = len(data.get("macro_news", []))
    stock_n = len(data.get("stock_news", []))
    st.caption(f"宏观 {macro_n} 条 · 个股 {stock_n} 条")

    if summary:
        st.markdown("**AI 每日要点**")
        st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)
    else:
        reason = summary_data.get("error") or summary_data.get("reason")
        if reason:
            if "402" in str(reason) or "Insufficient Balance" in str(reason):
                msg = "DeepSeek 账户余额不足，请充值后点击刷新重新生成总结。"
            else:
                msg = f"AI 总结未生成: {reason}"
            st.markdown(f'<div class="err-box">{msg}</div>', unsafe_allow_html=True)

    tab_macro, tab_stock = st.tabs(["宏观", "个股"])
    with tab_macro:
        macro = data.get("macro_news", [])
        if not macro:
            st.info("暂无宏观新闻（请确认 TAVILY_API_KEY 后点击刷新）")
        for article in macro[:12]:
            render_news_card(article)
    with tab_stock:
        stock_news = data.get("stock_news", [])
        if not stock_news:
            st.info("暂无个股新闻")
        for article in stock_news[:20]:
            render_news_card(article, show_ticker=True)


@st.dialog("AI 助手", width="large")
def ai_chat_dialog(data: dict):
    llm = DeepSeekClient(get_config().deepseek)
    if not llm.is_configured:
        st.warning("请配置 DEEPSEEK_API_KEY（.env 或 Streamlit Secrets）")
        return

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    ctx = build_dashboard_context(data)
    for msg in st.session_state.chat_history[-8:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if question := st.chat_input("基于看板提问…"):
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("思考中…"):
                try:
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history[:-1]
                    ]
                    answer = llm.ask_about_dashboard(question, ctx, history)
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(str(e))

    if st.session_state.chat_history and st.button("清空对话", key="clear_chat_dialog"):
        st.session_state.chat_history = []
        st.rerun()


def render_floating_chat(data: dict):
    if st.button("💬", key="chat_fab", help="打开 AI 助手"):
        ai_chat_dialog(data)


def main():
    inject_css()
    data = load_cached_data()
    page = render_sidebar_nav(data)
    render_header(data)

    if page == "market":
        render_market_page(data)
    else:
        render_news_page(data)

    render_floating_chat(data)


if __name__ == "__main__":
    main()
