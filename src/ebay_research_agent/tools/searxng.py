import json

import httpx
from langchain_core.tools import tool


class SearXNGClient:
    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient()

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        response = await self._client.get(
            f"{self.base_url}/search",
            params={"q": query, "format": "json"},
        )
        response.raise_for_status()
        return [
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
            }
            for result in response.json().get("results", [])[:limit]
        ]


def build_search_tool(client: SearXNGClient):
    @tool
    async def search_web(query: str, limit: int = 10) -> str:
        """Search the web for a given query.

        Args:
            query: The search query.
            limit: Maximum number of results to return.
        """
        results = await client.search(query, limit)
        return json.dumps(results)

    return search_web
