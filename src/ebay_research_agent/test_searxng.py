import asyncio

import httpx

from ebay_research_agent.tools.searxng import SearXNGClient


def test_search_builds_request_and_parses() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Wii repair guide",
                        "url": "https://example.com/1",
                        "content": "summary",
                    },
                    {
                        "title": "Switch teardown",
                        "url": "https://example.com/2",
                        "content": "summary",
                    },
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = SearXNGClient(
        "https://searx.example.com", client=httpx.AsyncClient(transport=transport)
    )
    results = asyncio.run(client.search("wii common issues", limit=1))
    assert "https://searx.example.com/search" in captured["url"]
    assert "q=wii+common+issues" in captured["url"]
    assert "format=json" in captured["url"]
    assert results == [
        {
            "title": "Wii repair guide",
            "url": "https://example.com/1",
            "content": "summary",
        }
    ]


def test_search_parses_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    transport = httpx.MockTransport(handler)
    client = SearXNGClient(
        "https://searx.example.com", client=httpx.AsyncClient(transport=transport)
    )
    assert asyncio.run(client.search("nothing")) == []
