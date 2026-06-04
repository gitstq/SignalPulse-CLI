# SignalPulse-CLI

Lightweight terminal-based cross-platform social signal aggregation and AI-powered briefing engine.

## Features

- **Multi-source aggregation**: Hacker News, Reddit, GitHub Trending, Product Hunt
- **Smart scoring**: Cross-platform normalized engagement scoring
- **AI synthesis**: Configurable LLM-powered intelligence briefings (OpenAI/Anthropic/Ollama)
- **Beautiful TUI**: Rich terminal output with colored tables and progress bars
- **Multiple formats**: Terminal, Markdown, HTML reports
- **Local caching**: SQLite-based cache to minimize API calls
- **Zero heavy deps**: Only `requests` + `rich` beyond stdlib

## Installation

```bash
pip install -e .
```

Or install dependencies manually:

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Fetch trending signals
python -m signalpulse_cli fetch

# Generate AI briefing
python -m signalpulse_cli brief

# Generate HTML report
python -m signalpulse_cli report --format html -o report.html

# Initialize config
python -m signalpulse_cli config init
```

## Configuration

Copy `config.example.yaml` to `~/.signalpulse/config.yaml` and customize.

Set AI API key via environment variable:

```bash
export SIGNALPULSE_AI_API_KEY="your-api-key"
```

## License

MIT License
