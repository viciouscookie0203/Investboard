# Investboard 📊

宏观投资数据看板 — 基于 Streamlit，整合 FRED 宏观指标、飞书自选股、Tavily 新闻与 DeepSeek AI 分析。

## 功能

| 模块 | 数据源 | 说明 |
|------|--------|------|
| 宏观指标 | FRED API + 飞书配置表 | Score Card + 汽车仪表盘 Gauge，阈值 Color Code |
| 股票行情 | 飞书自选股 + yfinance | 最新价、涨跌幅、可视化柱状图 |
| 宏观新闻 | Tavily | 每日全球宏观与市场综述 |
| 个股新闻 | Tavily | 按自选股抓取，保留原始 URL |
| AI 总结 | DeepSeek | 新闻汇总 + 看板问答助手 |

## 项目结构

```
Investboard/
├── streamlit_app.py          # Streamlit 入口（Cloud 部署用此文件）
├── config/
│   └── settings.py           # 环境变量配置
├── src/
│   ├── data/
│   │   ├── feishu_client.py    # 飞书 Bitable 读取
│   │   ├── fred_client.py        # FRED 宏观数据
│   │   ├── tavily_client.py      # Tavily 新闻搜索
│   │   ├── stock_prices.py       # yfinance 股价
│   │   ├── cache.py              # JSON 本地缓存
│   │   └── pipeline.py           # 每日抓取编排
│   ├── llm/
│   │   └── deepseek_client.py    # DeepSeek LLM
│   ├── visualization/
│   │   ├── gauges.py             # Plotly 仪表盘
│   │   └── metrics_status.py     # 阈值状态判定
│   └── prompts/                  # LLM 提示词（自行填写）
│       ├── news_summary_system.txt
│       ├── news_summary_user.txt
│       └── chat_system.txt
├── scripts/
│   └── fetch_daily_data.py   # CLI 抓取脚本
├── data/cache/               # 缓存 JSON（GitHub Action 每日更新）
├── tests/                    # 单元测试
└── .github/workflows/
    ├── daily_update.yml      # 每日 8:00 自动抓取
    └── ci.yml                # PR 测试
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Keys
```

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `FEISHU_APP_TOKEN` | Bitable App Token |
| `FEISHU_STOCK_TABLE_ID` | 股票表 ID |
| `FEISHU_METRIC_TABLE_ID` | 指标配置表 ID |
| `FRED_API_KEY` | FRED API Key |
| `TAVILY_API_KEY` | Tavily API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（留空则跳过 AI 功能） |

### 3. 飞书表格字段

**股票表** (`FEISHU_STOCK_TABLE_ID`)：

| 字段 | 说明 | 示例 |
|------|------|------|
| Ticker / 代码 | 股票代码 | AAPL, 0700.HK |
| Name / 名称 | 公司名称 | Apple |
| Market / 市场 | 可选 | US, HK |

**指标表** (`FEISHU_METRIC_TABLE_ID`)：

| 字段 | 说明 | 示例 |
|------|------|------|
| Series ID | FRED 序列 ID | UNRATE, CPIAUCSL |
| Name / 名称 | 显示名称 | 失业率 |
| Unit / 单位 | 单位 | % |
| Warn Low / 预警下限 | 黄色阈值 | 3.0 |
| Warn High / 预警上限 | 黄色阈值 | 5.0 |
| Danger Low / 危险下限 | 红色阈值 | 2.0 |
| Danger High / 危险上限 | 红色阈值 | 6.0 |
| Min / Max | 仪表盘范围 | 0, 10 |
| Direction | 方向提示 | lower_is_better |

### 4. 运行

```bash
# 首次抓取数据
python scripts/fetch_daily_data.py

# 启动看板
streamlit run streamlit_app.py
```

浏览器访问 `http://localhost:8501`

### 5. 自定义 LLM 提示词

编辑 `src/prompts/` 下的文件（`#` 开头的行会被忽略）：

- `news_summary_system.txt` — 新闻总结系统提示
- `news_summary_user.txt` — 用户提示，使用 `{{CONTEXT}}` 占位符
- `chat_system.txt` — 看板问答助手系统提示

## 部署

### Streamlit Cloud

1. Push 到 GitHub
2. 在 [share.streamlit.io](https://share.streamlit.io) 创建 App
3. Main file: `streamlit_app.py`
4. 在 Secrets 中填入 API Keys（参考 `.streamlit/secrets.toml.example`）

### GitHub Actions 每日自动更新

Workflow 文件：`.github/workflows/daily_update.yml`

- **时间**：每天 08:00 (Asia/Shanghai)
- **操作**：抓取全部数据 → 写入 `data/cache/` → 自动 commit

在 GitHub Repository → Settings → Secrets 中添加：

```
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_APP_TOKEN
FEISHU_STOCK_TABLE_ID
FEISHU_METRIC_TABLE_ID
FRED_API_KEY
TAVILY_API_KEY
DEEPSEEK_API_KEY
```

## 测试

```bash
pytest tests/ -v
```

## 技术栈

- **Frontend**: Streamlit + Plotly
- **Data**: FRED, Tavily, yfinance, 飞书 Bitable
- **LLM**: DeepSeek (OpenAI-compatible)
- **CI/CD**: GitHub Actions
