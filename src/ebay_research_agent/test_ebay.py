import asyncio
import base64

import httpx

from ebay_research_agent.tools.ebay import (
    EbayClient,
    base_url_for_env,
    build_enduserctx,
    build_search_filter,
    parse_item_summaries,
)


def test_base_url_for_env() -> None:
    assert base_url_for_env("sandbox") == "https://api.sandbox.ebay.com"
    assert base_url_for_env("production") == "https://api.ebay.com"


def test_build_search_filter() -> None:
    assert (
        build_search_filter(10, 50)
        == "conditionIds:{7000},price:[10..50],priceCurrency:USD"
    )


def test_build_search_filter_float() -> None:
    assert (
        build_search_filter(10.0, 50.5)
        == "conditionIds:{7000},price:[10..50.5],priceCurrency:USD"
    )


def test_build_enduserctx() -> None:
    assert (
        build_enduserctx("US", "19406")
        == "contextualLocation=country%3DUS%2Czip%3D19406"
    )


def test_parse_item_summaries() -> None:
    payload = {
        "itemSummaries": [
            {
                "title": "Broken Wii",
                "itemId": "v1|1|0",
                "shortDescription": "Does not power on",
                "price": {"value": "25.00", "currency": "USD"},
                "itemWebUrl": "https://ebay.com/itm/1",
                "condition": "For parts or not working",
                "shippingOptions": [
                    {
                        "shippingCostType": "CALCULATED",
                        "shippingCost": {"value": "12.50", "currency": "USD"},
                    }
                ],
            }
        ]
    }
    items = parse_item_summaries(payload)
    assert items == [
        {
            "title": "Broken Wii",
            "item_id": "v1|1|0",
            "short_description": "Does not power on",
            "price": "25.00",
            "currency": "USD",
            "url": "https://ebay.com/itm/1",
            "condition": "For parts or not working",
            "shipping_cost": "12.50",
            "shipping_currency": "USD",
            "shipping_cost_type": "CALCULATED",
            "total_cost": "37.50",
        }
    ]


def test_parse_item_summaries_free_shipping() -> None:
    payload = {
        "itemSummaries": [
            {
                "title": "Dead Switch",
                "price": {"value": "40.00", "currency": "USD"},
                "itemWebUrl": "https://ebay.com/itm/2",
                "shippingOptions": [
                    {
                        "shippingCostType": "FREE",
                        "shippingCost": {"value": "0.00", "currency": "USD"},
                    }
                ],
            }
        ]
    }
    items = parse_item_summaries(payload)
    assert items[0]["total_cost"] == "40.00"


def test_parse_item_summaries_no_shipping() -> None:
    payload = {
        "itemSummaries": [
            {
                "title": "Mystery Box",
                "price": {"value": "15.00", "currency": "USD"},
                "itemWebUrl": "https://ebay.com/itm/3",
            }
        ]
    }
    items = parse_item_summaries(payload)
    assert items[0]["shipping_cost"] is None
    assert items[0]["shipping_cost_type"] is None
    assert items[0]["total_cost"] == "15.00"


def test_parse_item_summaries_empty() -> None:
    assert parse_item_summaries({}) == []


def test_get_access_token_basic_auth() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})

    transport = httpx.MockTransport(handler)
    client = EbayClient(
        "https://api.ebay.com",
        "app",
        "cert",
        client=httpx.AsyncClient(transport=transport),
    )
    token = asyncio.run(client.get_access_token())
    assert token == "tok"
    expected = base64.b64encode(b"app:cert").decode()
    assert captured["auth"] == f"Basic {expected}"
    assert "grant_type=client_credentials" in captured["body"]


def test_search_for_parts_builds_request_and_parses() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["marketplace"] = request.headers["X-EBAY-C-MARKETPLACE-ID"]
        captured["enduserctx"] = request.headers.get("X-EBAY-C-ENDUSERCTX")
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "title": "Dead Switch",
                        "price": {"value": "40.00", "currency": "USD"},
                        "itemWebUrl": "https://ebay.com/itm/2",
                        "shippingOptions": [
                            {
                                "shippingCostType": "FIXED",
                                "shippingCost": {"value": "9.99", "currency": "USD"},
                            }
                        ],
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = EbayClient(
        "https://api.ebay.com",
        "app",
        "cert",
        zip_code="19406",
        client=httpx.AsyncClient(transport=transport),
    )
    items = asyncio.run(client.search_for_parts("switch", 10, 80, limit=5))
    assert captured["auth"] == "Bearer tok"
    assert captured["marketplace"] == "EBAY_US"
    assert captured["enduserctx"] == "contextualLocation=country%3DUS%2Czip%3D19406"
    assert "/buy/browse/v1/item_summary/search" in captured["url"]
    assert "q=switch" in captured["url"]
    assert "limit=5" in captured["url"]
    assert "conditionIds" in captured["url"]
    assert items[0]["title"] == "Dead Switch"
    assert items[0]["price"] == "40.00"
    assert items[0]["shipping_cost"] == "9.99"
    assert items[0]["total_cost"] == "49.99"


def test_search_for_parts_omits_enduserctx_without_zip() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})
        captured["enduserctx"] = request.headers.get("X-EBAY-C-ENDUSERCTX")
        return httpx.Response(200, json={"itemSummaries": []})

    transport = httpx.MockTransport(handler)
    client = EbayClient(
        "https://api.ebay.com",
        "app",
        "cert",
        client=httpx.AsyncClient(transport=transport),
    )
    asyncio.run(client.search_for_parts("switch", 10, 80))
    assert captured.get("enduserctx") is None


def test_search_for_parts_detailed_enriches_description() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})
        if request.url.path.startswith("/buy/browse/v1/item/"):
            captured["item_calls"] = captured.get("item_calls", []) + [
                str(request.url.path)
            ]
            return httpx.Response(200, json={"description": "Broken disc drive"})
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "itemId": "v1|1|0",
                        "title": "Broken Wii",
                        "price": {"value": "25.00", "currency": "USD"},
                        "itemWebUrl": "https://ebay.com/itm/1",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = EbayClient(
        "https://api.ebay.com",
        "app",
        "cert",
        client=httpx.AsyncClient(transport=transport),
    )
    items = asyncio.run(client.search_for_parts_detailed("wii", 10, 80))
    assert items[0]["description"] == "Broken disc drive"
    assert captured["item_calls"] == ["/buy/browse/v1/item/v1|1|0"]


def test_search_for_parts_detailed_skips_failed_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})
        if request.url.path.startswith("/buy/browse/v1/item/"):
            return httpx.Response(500)
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "itemId": "v1|1|0",
                        "title": "Broken Wii",
                        "price": {"value": "25.00", "currency": "USD"},
                        "itemWebUrl": "https://ebay.com/itm/1",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = EbayClient(
        "https://api.ebay.com",
        "app",
        "cert",
        client=httpx.AsyncClient(transport=transport),
    )
    items = asyncio.run(client.search_for_parts_detailed("wii", 10, 80))
    assert "description" not in items[0]
    assert items[0]["title"] == "Broken Wii"
