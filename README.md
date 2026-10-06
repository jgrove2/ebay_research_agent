# Repair Agent

A LangGraph agent powered by DeepSeek that researches the common issues and
failure points of game consoles. It fans out one worker per product; each worker
first checks its own knowledge, then searches DuckDuckGo via an MCP server when
unsure, and returns the issues plus a "for-parts" blurb describing what to look
for when browsing eBay parts/repair listings.

## Prerequisites

- Python 3.12
- Node.js >= 18 (the DuckDuckGo MCP server runs via `npx`)

## Setup

1. Install dependencies:

   ```sh
   uv sync
   ```

2. Configure your API key and products:

   ```sh
   cp .env.example .env
   # then edit .env and set DEEPSEEK_API_KEY
   # optionally set PRODUCTS (comma-separated) and MCP_SERVERS (JSON)
   ```

## Run

```sh
uv run repair-agent
```

Or via the module:

```sh
uv run python -m ebay_research_agent
```

Print the graph diagram:

```sh
uv run repair-agent --diagram
```

## Test

```sh
uv run pytest
```
