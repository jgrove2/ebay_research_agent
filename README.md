# Repair Agent

A LangGraph agent powered by DeepSeek.

## Setup

1. Install dependencies:

   ```sh
   uv sync
   ```

2. Configure your API key:

   ```sh
   cp .env.example .env
   # then edit .env and set DEEPSEEK_API_KEY
   ```

## Run

```sh
uv run python -m repair_agent
```

Or via the console script:

```sh
uv run repair-agent
```

## Test

```sh
uv run pytest
```
