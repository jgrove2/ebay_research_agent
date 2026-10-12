import asyncio

import httpx

from ebay_research_agent.config import Settings
from ebay_research_agent.ingest import LogtoTokenSource, post_listings


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPError("request failed")

    def json(self) -> dict:
        return self._payload


class FakeClient:
    def __init__(self, response: FakeResponse | None = None) -> None:
        self._response = response
        self.posts: list[tuple[str, dict]] = []
        self.closed = False

    async def post(self, url: str, **kwargs) -> FakeResponse:
        self.posts.append((url, kwargs))
        assert self._response is not None
        return self._response

    async def aclose(self) -> None:
        self.closed = True


class FakeTokenSource:
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token
        self.calls = 0

    async def get_access_token(self) -> str | None:
        self.calls += 1
        return self._token


def _settings(**overrides: str) -> Settings:
    base = {
        "repair_lab_api_url": "http://localhost:8787",
        "logto_endpoint": "https://auth.example.com",
        "logto_api_resource": "https://api.example.com",
        "logto_client_id": "client-id",
        "logto_client_secret": "client-secret",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_post_listings_noops_without_api_url() -> None:
    settings = _settings(repair_lab_api_url="")
    result = asyncio.run(post_listings({"wii": []}, settings))
    assert result is None


def test_post_listings_skips_without_logto_credentials() -> None:
    settings = _settings(logto_client_id="", logto_client_secret="")
    result = asyncio.run(post_listings({"wii": []}, settings))
    assert result is None


def test_post_listings_sends_combined_payload() -> None:
    settings = _settings()
    response = FakeResponse({"inserted": 2, "updated": 1, "total": 3})
    client = FakeClient(response)
    source = FakeTokenSource("tok")

    result = asyncio.run(
        post_listings({"wii": [{"title": "x"}]}, settings, client=client, token_source=source)
    )

    assert result == {"inserted": 2, "updated": 1, "total": 3}
    assert source.calls == 1
    assert len(client.posts) == 1
    url, kwargs = client.posts[0]
    assert url == "http://localhost:8787/listings"
    assert kwargs["json"] == {"wii": [{"title": "x"}]}
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}
    assert client.closed is False


def test_post_listings_strips_trailing_slash() -> None:
    settings = _settings(repair_lab_api_url="http://localhost:8787/")
    client = FakeClient(FakeResponse({"inserted": 0, "updated": 0, "total": 0}))
    result = asyncio.run(
        post_listings({}, settings, client=client, token_source=FakeTokenSource("tok"))
    )
    assert result is not None
    assert client.posts[0][0] == "http://localhost:8787/listings"


def test_post_listings_returns_none_on_token_failure() -> None:
    settings = _settings()
    client = FakeClient()
    result = asyncio.run(
        post_listings({"wii": []}, settings, client=client, token_source=FakeTokenSource(None))
    )
    assert result is None
    assert client.posts == []


def test_post_listings_returns_none_on_http_error() -> None:
    settings = _settings()
    client = FakeClient(FakeResponse({}, status=500))
    result = asyncio.run(
        post_listings({"wii": []}, settings, client=client, token_source=FakeTokenSource("tok"))
    )
    assert result is None


def test_token_source_requests_and_caches_token() -> None:
    client = FakeClient(FakeResponse({"access_token": "tok", "expires_in": 3600}))
    source = LogtoTokenSource(
        "https://auth.example.com", "https://api.example.com", "client-id", "secret",
        client=client,
    )

    first = asyncio.run(source.get_access_token())
    second = asyncio.run(source.get_access_token())

    assert first == "tok"
    assert second == "tok"
    assert len(client.posts) == 1
    url, kwargs = client.posts[0]
    assert url == "https://auth.example.com/oidc/token"
    assert kwargs["headers"] == {"Content-Type": "application/x-www-form-urlencoded"}
    assert kwargs["data"]["grant_type"] == "client_credentials"
    assert kwargs["data"]["client_id"] == "client-id"
    assert kwargs["data"]["client_secret"] == "secret"
    assert kwargs["data"]["resource"] == "https://api.example.com"
    assert kwargs["data"]["scope"] == "all"


def test_token_source_returns_none_on_http_error() -> None:
    client = FakeClient(FakeResponse({}, status=401))
    source = LogtoTokenSource(
        "https://auth.example.com", "https://api.example.com", "client-id", "secret",
        client=client,
    )
    assert asyncio.run(source.get_access_token()) is None
