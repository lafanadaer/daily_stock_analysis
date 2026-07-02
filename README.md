# AI News Digest

[![CI](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🤖 基于 AI 大模型的技术资讯 RSS 摘要推送服务，每 48 小时抓取全球顶级技术博客，LLM 评分/摘要后推送到多渠道

[**快速开始**](#-快速开始) · [**推送效果**](#-推送效果) · [**更新日志**](docs/CHANGELOG.md)

## ✨ 功能特性

- 📰 **90+ RSS 源**：覆盖 Hacker News 顶级技术博客（simonwillison, paulgraham, krebsonsecurity 等）
- 🤖 **AI 精选**：LLM 多维度评分（相关性/质量/时效性）+ 自动分类 + 中文摘要
- 📊 **可视化报告**：Mermaid 图表（分类饼图、关键词柱状图）+ Tag 云
- 🔔 **12 渠道推送**：企业微信、飞书、Telegram、Discord、Slack、邮件、Pushover、PushPlus、Server酱3、AstrBot、钉钉、自定义 Webhook
- ⏱️ **48h 间隔**：默认每 48 小时推送一次，可通过配置调整
- 🐳 **Docker 支持**：一键部署到 NAS/服务器

## 🚀 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少配置：
- 一个 LLM API Key（Gemini / OpenAI / Anthropic / DeepSeek）
- 一个通知渠道（Telegram / 企业微信 / 飞书 等）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行

```bash
# 单次运行
python main.py

# 调试模式（不发送通知）
python main.py --debug --no-notify

# 定时模式（默认每48小时执行）
python main.py --schedule
```

### 4. Docker 部署

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 5. GitHub Actions

Fork 本仓库，在 Settings → Secrets 中配置 `GEMINI_API_KEY` 和需要的通知渠道 secret。默认每 2 天 UTC 10:00（北京时间 18:00）自动推送。

## 📊 推送效果

AI Digest 报告包含：
- 🏆 **Top 3 必读**：评分最高的 3 篇文章
- 📈 **趋势概览**：3-5 句宏观技术趋势总结
- 📂 **分类汇总**：AI/ML、安全、工程、工具、观点等分类
- 🏷️ **关键词云**：高频技术关键词

## 📁 项目结构

```
├── main.py                 # 入口
├── src/
│   ├── config.py           # 配置管理
│   ├── scheduler.py        # 定时调度（支持 24h/48h/自定义间隔）
│   ├── notification.py     # 多渠道通知服务
│   ├── notification_sender/ # 12 个通知渠道实现
│   ├── services/
│   │   └── ai_daily_digest.py  # AI Digest 核心服务
│   └── core/
│       └── config_registry.py  # 配置注册表
├── api/                    # FastAPI 管理接口
├── .github/workflows/      # GitHub Actions 自动推送
├── docker/                 # Docker 部署文件
└── scripts/                # 工具脚本
```

## ⚙️ 关键配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DIGEST_INTERVAL_HOURS` | `48` | 推送间隔（24=每天，48=每2天） |
| `AI_DAILY_DIGEST_DAYS` | `2` | 文章抓取窗口（天） |
| `AI_DAILY_DIGEST_TOP_N` | `15` | 精选文章数量 |
| `AI_DAILY_DIGEST_LANGUAGE` | `zh` | 输出语言（zh/en） |
| `SCHEDULE_TIME` | `18:00` | 定时执行时间 |

完整配置见 [.env.example](.env.example)

## 📄 许可证

[MIT](LICENSE)
