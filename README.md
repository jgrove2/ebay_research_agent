# Repair Agent

A LangGraph agent powered by DeepSeek that researches the common issues and
failure points of game consoles. It fans out one worker per product; each worker
first checks its own knowledge, then searches the web via a self-hosted SearXNG
instance when unsure, and returns the issues plus a "for-parts" blurb describing
what to look for when browsing eBay parts/repair listings.

## Prerequisites

- Python 3.12
- Docker (to run SearXNG)

## Setup

1. Start SearXNG:

   ```sh
   docker compose up -d
   ```

   Verify it is up by opening http://localhost:8080 or running:

   ```sh
   curl 'http://localhost:8080/search?q=test&format=json'
   ```

2. Install dependencies:

   ```sh
   uv sync
   ```

3. Configure your API key and products:

   ```sh
   cp .env.example .env
   # then edit .env and set DEEPSEEK_API_KEY
   # optionally set PRODUCTS (comma-separated) and SEARXNG_URL
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
