<div align="center">

# 🚀 SignalPulse-CLI

**轻量级终端跨平台社交信号聚合与AI智能简报引擎**
**Lightweight Terminal-Based Cross-Platform Social Signal Aggregation & AI-Powered Briefing Engine**
**輕量級終端跨平台社交信號聚合與AI智能簡報引擎**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)]()

[🌐 简体中文](#-简体中文--chinese-simplified) | [🌐 繁體中文](#-繁體中文--chinese-traditional) | [🌐 English](#-english)

---

<p align="center">
  <img src="https://img.shields.io/badge/Hacker_News-🔥-orange?style=flat-square" alt="HN"/>
  <img src="https://img.shields.io/badge/Reddit-💬-red?style=flat-square" alt="Reddit"/>
  <img src="https://img.shields.io/badge/GitHub-⭐-black?style=flat-square" alt="GitHub"/>
  <img src="https://img.shields.io/badge/Product_Hunt-🚀-ff6154?style=flat-square" alt="PH"/>
  <img src="https://img.shields.io/badge/AI_Briefing-🤖-purple?style=flat-square" alt="AI"/>
</p>

</div>

---

## 🌐 简体中文 (Chinese Simplified)

### 🎉 项目介绍

**SignalPulse-CLI** 是一款轻量级终端工具，能够跨多个主流平台（Hacker News、Reddit、GitHub Trending、Product Hunt）并行抓取热门话题，通过**真实用户参与度**（点赞、评论、分享）而非SEO排名进行智能评分排序，最终借助AI大模型生成结构化的情报简报。

**解决的核心痛点**：
- 🔍 信息碎片化：技术人每天需要在5+平台手动追踪热点，效率极低
- 📊 噪音太多：搜索引擎返回的是SEO优化内容，而非真实用户关注的话题
- 🤖 AI赋能不足：缺少将多源信息聚合后用AI提炼洞察的工具

**自研差异化亮点**：
- ✅ **纯Python实现**，零重型依赖，仅需 `requests` + `rich`
- ✅ **跨平台评分归一化**，不同平台的点赞/评论数据统一到0-1分值体系
- ✅ **时间衰减算法**，越新的内容权重越高，避免陈旧信息干扰
- ✅ **SQLite本地缓存**，避免重复API调用，支持离线浏览
- ✅ **多格式输出**：终端TUI、Markdown报告、完整HTML报告
- ✅ **多LLM兼容**：支持OpenAI、Anthropic、Ollama等所有OpenAI兼容API

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔥 **多源并行聚合** | 同时从HN、Reddit、GitHub、ProductHunt抓取数据 |
| 📊 **智能评分引擎** | 跨平台Min-Max归一化 + 时间衰减 + 可配置权重 |
| 🤖 **AI简报合成** | 一键生成结构化情报简报（趋势/热点/新兴信号/建议） |
| 🖥️ **Rich终端TUI** | 彩色表格、进度条、面板化输出，终端体验极佳 |
| 📝 **多格式报告** | 支持Terminal、Markdown、HTML三种输出格式 |
| 💾 **SQLite缓存** | 本地缓存1小时（可配置），减少API调用 |
| ⚙️ **灵活配置** | YAML配置文件 + 环境变量 + CLI参数三层覆盖 |
| 🛡️ **优雅降级** | 单个数据源失败不影响其他源，确保始终有输出 |

### 🚀 快速开始

**环境要求**：
- Python 3.9+
- pip（Python包管理器）

**安装步骤**：

```bash
# 克隆仓库
git clone https://github.com/gitstq/SignalPulse-CLI.git
cd SignalPulse-CLI

# 安装依赖
pip install -r requirements.txt

# 或一键安装为命令行工具
pip install -e .
```

**使用命令**：

```bash
# 🔥 获取各平台热门信号（默认全部数据源）
signalpulse fetch

# 📊 仅从Hacker News获取，限制20条
signalpulse fetch --sources hn --limit 20

# 🤖 生成AI智能简报（需配置API Key）
signalpulse brief

# 📝 导出Markdown报告
signalpulse report --format markdown -o briefing.md

# 🌐 导出HTML报告
signalpulse report --format html -o briefing.html

# ⚙️ 初始化配置文件
signalpulse config init

# ⚙️ 查看当前配置
signalpulse config show
```

### 📖 详细使用指南

#### 配置AI API Key

复制示例配置文件并编辑：

```bash
# 初始化配置
signalpulse config init

# 编辑配置文件
nano ~/.signalpulse/config.yaml
```

或通过环境变量设置：

```bash
export SIGNALPULSE_AI_API_KEY="sk-your-api-key"
export SIGNALPULSE_AI_BASE_URL="https://api.openai.com/v1"  # 可选，支持自定义端点
export SIGNALPULSE_AI_MODEL="gpt-4o"  # 可选，默认gpt-4o
```

#### 使用Ollama本地模型

```yaml
# ~/.signalpulse/config.yaml
ai:
  api_key: "ollama"  # Ollama不需要真实key
  base_url: "http://localhost:11434/v1"
  model: "llama3"
```

#### 自定义数据源权重

```yaml
# ~/.signalpulse/config.yaml
sources:
  hackernews:
    enabled: true
    weight: 1.2    # 提升HN权重
  reddit:
    enabled: true
    weight: 1.0
    subreddits:
      - technology
      - programming
      - machinelearning
  github:
    enabled: true
    weight: 0.8
  producthunt:
    enabled: false   # 禁用PH
```

#### 评分算法说明

SignalPulse使用加权综合评分公式：

```
最终得分 = w_score × 归一化分数 + w_comments × 归一化评论数 + w_recency × 时间衰减
```

- **归一化**：每个平台内部Min-Max归一化到[0,1]，消除平台间量纲差异
- **时间衰减**：指数衰减模型，半衰期默认12小时，越新内容得分越高
- **权重可配**：默认分数50%、评论30%、时效20%，可在配置中自定义

### 💡 设计思路与迭代规划

**设计理念**：
- **信号优于搜索**：用真实用户行为（点赞/评论）代替SEO排名，发现真正值得关注的内容
- **聚合优于单源**：跨平台对比才能看到全局趋势，避免信息茧房
- **AI增强而非替代**：AI负责提炼和总结，最终判断权留给用户
- **轻量优于重型**：纯Python实现，零ML依赖，安装即用

**后续迭代计划**：
- 📌 v1.1：新增Twitter/X数据源、支持RSS自定义源
- 📌 v1.2：新增关键词过滤和正则匹配规则
- 📌 v1.3：新增定时任务模式（cron-like自动抓取）
- 📌 v1.4：新增JSON输出格式，方便与其他工具集成
- 📌 v2.0：新增Web Dashboard可视化界面

### 📦 打包与部署指南

本项目为**CLI工具库**类型，无需打包为可执行文件。

```bash
# 安装为全局命令行工具
pip install -e .

# 验证安装
signalpulse --version
signalpulse --help

# 卸载
pip uninstall signalpulse-cli
```

**兼容环境**：
- ✅ Python 3.9 / 3.10 / 3.11 / 3.12 / 3.13
- ✅ Windows / macOS / Linux
- ✅ 无需Docker、无需数据库服务器

### 🤝 贡献指南

欢迎贡献代码！请遵循以下规范：

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feat/amazing-feature`
3. 提交更改：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feat/amazing-feature`
5. 提交 **Pull Request**

**提交规范**（Angular Convention）：
- `feat:` 新增功能
- `fix:` 修复问题
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链更新

### 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 🌐 繁體中文 (Chinese Traditional)

### 🎉 專案介紹

**SignalPulse-CLI** 是一款輕量級終端工具，能夠跨多個主流平台（Hacker News、Reddit、GitHub Trending、Product Hunt）並行抓取熱門話題，透過**真實使用者參與度**（點讚、留言、分享）而非SEO排名進行智慧評分排序，最終借助AI大模型生成結構化的情報簡報。

**解決的核心痛點**：
- 🔍 資訊碎片化：技術人每天需要在5+平台手動追蹤熱點，效率極低
- 📊 噪音太多：搜尋引擎返回的是SEO優化內容，而非真實使用者關注的話題
- 🤖 AI賦能不足：缺少將多源資訊聚合後用AI提煉洞察的工具

**自研差異化亮點**：
- ✅ **純Python實作**，零重型依賴，僅需 `requests` + `rich`
- ✅ **跨平台評分歸一化**，不同平台的點讚/留言資料統一到0-1分值體系
- ✅ **時間衰減演算法**，越新的內容權重越高，避免陳舊資訊干擾
- ✅ **SQLite本地快取**，避免重複API呼叫，支援離線瀏覽
- ✅ **多格式輸出**：終端TUI、Markdown報告、完整HTML報告
- ✅ **多LLM相容**：支援OpenAI、Anthropic、Ollama等所有OpenAI相容API

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔥 **多源並行聚合** | 同時從HN、Reddit、GitHub、ProductHunt抓取資料 |
| 📊 **智慧評分引擎** | 跨平台Min-Max歸一化 + 時間衰減 + 可配置權重 |
| 🤖 **AI簡報合成** | 一鍵生成結構化情報簡報（趨勢/熱點/新興信號/建議） |
| 🖥️ **Rich終端TUI** | 彩色表格、進度條、面板化輸出，終端體驗極佳 |
| 📝 **多格式報告** | 支援Terminal、Markdown、HTML三種輸出格式 |
| 💾 **SQLite快取** | 本地快取1小時（可配置），減少API呼叫 |
| ⚙️ **靈活配置** | YAML配置檔 + 環境變數 + CLI參數三層覆蓋 |
| 🛡️ **優雅降級** | 單個資料源失敗不影響其他源，確保始終有輸出 |

### 🚀 快速開始

**環境要求**：
- Python 3.9+
- pip（Python套件管理器）

**安裝步驟**：

```bash
# 克隆倉庫
git clone https://github.com/gitstq/SignalPulse-CLI.git
cd SignalPulse-CLI

# 安裝依賴
pip install -r requirements.txt

# 或一鍵安裝為命令列工具
pip install -e .
```

**使用命令**：

```bash
# 🔥 獲取各平台熱門信號（預設全部資料源）
signalpulse fetch

# 📊 僅從Hacker News獲取，限制20條
signalpulse fetch --sources hn --limit 20

# 🤖 生成AI智慧簡報（需配置API Key）
signalpulse brief

# 📝 匯出Markdown報告
signalpulse report --format markdown -o briefing.md

# 🌐 匯出HTML報告
signalpulse report --format html -o briefing.html

# ⚙️ 初始化配置檔
signalpulse config init

# ⚙️ 查看當前配置
signalpulse config show
```

### 📖 詳細使用指南

#### 配置AI API Key

複製範例配置檔並編輯：

```bash
# 初始化配置
signalpulse config init

# 編輯配置檔
nano ~/.signalpulse/config.yaml
```

或透過環境變數設定：

```bash
export SIGNALPULSE_AI_API_KEY="sk-your-api-key"
export SIGNALPULSE_AI_BASE_URL="https://api.openai.com/v1"  # 可選，支援自訂端點
export SIGNALPULSE_AI_MODEL="gpt-4o"  # 可選，預設gpt-4o
```

#### 使用Ollama本地模型

```yaml
# ~/.signalpulse/config.yaml
ai:
  api_key: "ollama"  # Ollama不需要真實key
  base_url: "http://localhost:11434/v1"
  model: "llama3"
```

#### 評分演算法說明

SignalPulse使用加權綜合評分公式：

```
最終得分 = w_score × 歸一化分數 + w_comments × 歸一化留言數 + w_recency × 時間衰減
```

- **歸一化**：每個平台內部Min-Max歸一化到[0,1]，消除平台間量綱差異
- **時間衰減**：指數衰減模型，半衰期預設12小時，越新內容得分越高
- **權重可配**：預設分數50%、留言30%、時效20%，可在配置中自訂

### 💡 設計思路與迭代規劃

**設計理念**：
- **信號優於搜尋**：用真實使用者行為（點讚/留言）代替SEO排名，發現真正值得關注的內容
- **聚合優於單源**：跨平台對比才能看到全域趨勢，避免資訊繭房
- **AI增強而非替代**：AI負責提煉和總結，最終判斷權留給使用者
- **輕量優於重型**：純Python實作，零ML依賴，安裝即用

**後續迭代計畫**：
- 📌 v1.1：新增Twitter/X資料源、支援RSS自訂源
- 📌 v1.2：新增關鍵字過濾和正則匹配規則
- 📌 v1.3：新增定時任務模式（cron-like自動抓取）
- 📌 v1.4：新增JSON輸出格式，方便與其他工具整合
- 📌 v2.0：新增Web Dashboard視覺化介面

### 📦 打包與部署指南

本專案為**CLI工具庫**類型，無需打包為可執行檔。

```bash
# 安裝為全域命令列工具
pip install -e .

# 驗證安裝
signalpulse --version
signalpulse --help

# 解除安裝
pip uninstall signalpulse-cli
```

**相容環境**：
- ✅ Python 3.9 / 3.10 / 3.11 / 3.12 / 3.13
- ✅ Windows / macOS / Linux
- ✅ 無需Docker、無需資料庫伺服器

### 🤝 貢獻指南

歡迎貢獻程式碼！請遵循以下規範：

1. **Fork** 本倉庫
2. 建立特性分支：`git checkout -b feat/amazing-feature`
3. 提交變更：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feat/amazing-feature`
5. 提交 **Pull Request**

**提交規範**（Angular Convention）：
- `feat:` 新增功能
- `fix:` 修復問題
- `docs:` 文件更新
- `refactor:` 程式碼重構
- `test:` 測試相關
- `chore:` 建構/工具鏈更新

### 📄 開源協議

本專案基於 [MIT License](LICENSE) 開源。

---

## 🌐 English

### 🎉 Introduction

**SignalPulse-CLI** is a lightweight terminal tool that fetches trending topics across multiple major platforms (Hacker News, Reddit, GitHub Trending, Product Hunt) in parallel, ranks them by **real user engagement** (upvotes, comments, shares) rather than SEO rankings, and generates structured intelligence briefings using AI large language models.

**Core Pain Points Solved**:
- 🔍 **Information Fragmentation**: Developers manually track hot topics across 5+ platforms daily — extremely inefficient
- 📊 **Too Much Noise**: Search engines return SEO-optimized content, not what real users actually care about
- 🤖 **Insufficient AI Empowerment**: No tool exists that aggregates multi-source information and distills insights with AI

**Differentiation Highlights**:
- ✅ **Pure Python Implementation** — zero heavy dependencies, only `requests` + `rich`
- ✅ **Cross-Platform Score Normalization** — unifies upvotes/comments from different platforms into a 0-1 scale
- ✅ **Time Decay Algorithm** — newer content gets higher weight, preventing stale information from polluting results
- ✅ **SQLite Local Cache** — avoids redundant API calls, supports offline browsing
- ✅ **Multi-Format Output** — Terminal TUI, Markdown reports, full HTML reports
- ✅ **Multi-LLM Compatible** — supports OpenAI, Anthropic, Ollama, and all OpenAI-compatible APIs

### ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🔥 **Multi-Source Aggregation** | Fetches data from HN, Reddit, GitHub, ProductHunt simultaneously |
| 📊 **Smart Scoring Engine** | Cross-platform Min-Max normalization + time decay + configurable weights |
| 🤖 **AI Briefing Synthesis** | One-click structured intelligence briefings (trends/hot topics/emerging signals/recommendations) |
| 🖥️ **Rich Terminal TUI** | Colored tables, progress bars, panel-based output for an excellent terminal experience |
| 📝 **Multi-Format Reports** | Supports Terminal, Markdown, and HTML output formats |
| 💾 **SQLite Caching** | Local cache for 1 hour (configurable), minimizes API calls |
| ⚙️ **Flexible Configuration** | YAML config file + environment variables + CLI args — three-layer override |
| 🛡️ **Graceful Degradation** | Single source failure doesn't affect others — always produces output |

### 🚀 Quick Start

**Requirements**:
- Python 3.9+
- pip (Python package manager)

**Installation**:

```bash
# Clone the repository
git clone https://github.com/gitstq/SignalPulse-CLI.git
cd SignalPulse-CLI

# Install dependencies
pip install -r requirements.txt

# Or install as a CLI tool in one step
pip install -e .
```

**Usage**:

```bash
# 🔥 Fetch trending signals from all sources
signalpulse fetch

# 📊 Fetch only from Hacker News, limit to 20 items
signalpulse fetch --sources hn --limit 20

# 🤖 Generate AI-powered briefing (requires API key configuration)
signalpulse brief

# 📝 Export Markdown report
signalpulse report --format markdown -o briefing.md

# 🌐 Export HTML report
signalpulse report --format html -o briefing.html

# ⚙️ Initialize configuration file
signalpulse config init

# ⚙️ Show current configuration
signalpulse config show
```

### 📖 Detailed Usage Guide

#### Configuring AI API Key

Copy the example config and edit:

```bash
# Initialize config
signalpulse config init

# Edit config file
nano ~/.signalpulse/config.yaml
```

Or set via environment variables:

```bash
export SIGNALPULSE_AI_API_KEY="sk-your-api-key"
export SIGNALPULSE_AI_BASE_URL="https://api.openai.com/v1"  # Optional, supports custom endpoints
export SIGNALPULSE_AI_MODEL="gpt-4o"  # Optional, defaults to gpt-4o
```

#### Using Ollama Local Model

```yaml
# ~/.signalpulse/config.yaml
ai:
  api_key: "ollama"  # Ollama doesn't require a real key
  base_url: "http://localhost:11434/v1"
  model: "llama3"
```

#### Customizing Source Weights

```yaml
# ~/.signalpulse/config.yaml
sources:
  hackernews:
    enabled: true
    weight: 1.2    # Boost HN weight
  reddit:
    enabled: true
    weight: 1.0
    subreddits:
      - technology
      - programming
      - machinelearning
  github:
    enabled: true
    weight: 0.8
  producthunt:
    enabled: false   # Disable PH
```

#### Scoring Algorithm

SignalPulse uses a weighted composite scoring formula:

```
Final Score = w_score × Normalized Score + w_comments × Normalized Comments + w_recency × Time Decay
```

- **Normalization**: Min-Max normalization within each platform to [0,1], eliminating scale differences
- **Time Decay**: Exponential decay model with 12-hour half-life — newer content scores higher
- **Configurable Weights**: Default is 50% score, 30% comments, 20% recency — fully customizable

### 💡 Design Philosophy & Roadmap

**Design Principles**:
- **Signals Over Search**: Real user behavior (upvotes/comments) over SEO rankings — discover what truly matters
- **Aggregation Over Single Source**: Cross-platform comparison reveals global trends, avoiding filter bubbles
- **AI Augmentation, Not Replacement**: AI distills and summarizes; final judgment stays with the user
- **Lightweight Over Heavy**: Pure Python, zero ML dependencies — install and run

**Roadmap**:
- 📌 v1.1: Add Twitter/X data source, support custom RSS feeds
- 📌 v1.2: Add keyword filtering and regex matching rules
- 📌 v1.3: Add scheduled task mode (cron-like auto-fetch)
- 📌 v1.4: Add JSON output format for integration with other tools
- 📌 v2.0: Add Web Dashboard visualization interface

### 📦 Installation & Deployment Guide

This project is a **CLI tool/library** — no executable packaging required.

```bash
# Install as a global CLI tool
pip install -e .

# Verify installation
signalpulse --version
signalpulse --help

# Uninstall
pip uninstall signalpulse-cli
```

**Compatible Environments**:
- ✅ Python 3.9 / 3.10 / 3.11 / 3.12 / 3.13
- ✅ Windows / macOS / Linux
- ✅ No Docker required, no database server needed

### 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feat/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push the branch: `git push origin feat/amazing-feature`
5. Submit a **Pull Request**

**Commit Convention** (Angular Convention):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code refactoring
- `test:` Test-related changes
- `chore:` Build/toolchain updates

### 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Made with ❤️ by SOLO-AI-Agent | Inspired by the signal-over-noise philosophy**

</div>
