import base64
import json
import time

import httpx
from langchain_core.tools import tool

SANDBOX_BASE_URL = "https://api.sandbox.ebay.com"
PRODUCTION_BASE_URL = "https://api.ebay.com"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
FOR_PARTS_CONDITION_ID = "7000"


def base_url_for_env(env: str) -> str:
    return PRODUCTION_BASE_URL if env == "production" else SANDBOX_BASE_URL


def build_search_filter(min_price: float, max_price: float) -> str:
    return (
        f"conditionIds:{{{FOR_PARTS_CONDITION_ID}}},"
        f"price:[{_format_price(min_price)}..{_format_price(max_price)}],"
        "priceCurrency:USD"
    )


def build_enduserctx(country: str, zip_code: str) -> str:
    return f"contextualLocation=country%3D{country}%2Czip%3D{zip_code}"


def parse_item_summaries(payload: dict) -> list[dict]:
    return [_parse_item(item) for item in payload.get("itemSummaries", [])]


def _parse_item(item: dict) -> dict:
    shipping_options = item.get("shippingOptions") or []
    shipping = shipping_options[0] if shipping_options else {}
    shipping_cost = shipping.get("shippingCost", {}).get("value") if shipping else None
    price = item.get("price", {}).get("value")
    return {
        "title": item.get("title", ""),
        "price": price,
        "currency": item.get("price", {}).get("currency"),
        "url": item.get("itemWebUrl", ""),
        "condition": item.get("condition"),
        "shipping_cost": shipping_cost,
        "shipping_currency": (shipping.get("shippingCost", {}) or {}).get("currency"),
        "shipping_cost_type": shipping.get("shippingCostType"),
        "total_cost": _format_total(price, shipping_cost),
    }


def _format_total(price, shipping_cost) -> str | None:
    if price is None:
        return None
    try:
        total = float(price) + float(shipping_cost or 0)
    except (TypeError, ValueError):
        return None
    return f"{total:.2f}"


def _format_price(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class EbayClient:
    def __init__(
        self,
        base_url: str,
        app_id: str,
        cert_id: str,
        marketplace_id: str = "EBAY_US",
        zip_code: str = "",
        country: str = "US",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.cert_id = cert_id
        self.marketplace_id = marketplace_id
        self.zip_code = zip_code
        self.country = country
        self._client = client or httpx.AsyncClient()
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        credentials = base64.b64encode(
            f"{self.app_id}:{self.cert_id}".encode()
        ).decode()
        response = await self._client.post(
            f"{self.base_url}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": OAUTH_SCOPE},
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 7200)) - 60
        return self._access_token

    async def search_for_parts(
        self,
        query: str,
        min_price: float,
        max_price: float,
        limit: int = 20,
    ) -> list[dict]:
        token = await self.get_access_token()
        params = {
            "q": query,
            "limit": str(limit),
            "filter": build_search_filter(min_price, max_price),
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
        }
        if self.zip_code:
            headers["X-EBAY-C-ENDUSERCTX"] = build_enduserctx(self.country, self.zip_code)
        response = await self._client.get(
            f"{self.base_url}/buy/browse/v1/item_summary/search",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        return parse_item_summaries(response.json())


def build_ebay_tool(client: EbayClient):
    @tool
    async def search_ebay_for_parts(
        query: str,
        min_price: float,
        max_price: float,
        limit: int = 20,
    ) -> str:
        """Search eBay for 'for parts or not working' listings.

        Args:
            query: Search keywords (e.g. a game console name).
            min_price: Minimum listing price in USD.
            max_price: Maximum listing price in USD.
            limit: Maximum number of results to return.
        """
        items = await client.search_for_parts(query, min_price, max_price, limit)
        return json.dumps(items)

    return search_ebay_for_parts
