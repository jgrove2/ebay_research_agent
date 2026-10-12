import logging
import time

import httpx

from ebay_research_agent.config import Settings

logger = logging.getLogger(__name__)


class LogtoTokenSource:
    """Obtains (and caches) a Logto machine-to-machine access token.

    The Repair Lab API verifies Logto-issued JWTs by signature, issuer, and
    audience. A client-credentials grant against ``{endpoint}/oidc/token``
    yields exactly such a token for the configured API resource.
    """

    def __init__(
        self,
        endpoint: str,
        resource: str,
        client_id: str,
        client_secret: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._resource = resource
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = client or httpx.AsyncClient()
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def get_access_token(self) -> str | None:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        try:
            response = await self._client.post(
                f"{self._endpoint}/oidc/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "resource": self._resource,
                    "scope": "all",
                },
            )
            response.raise_for_status()
            payload = response.json()
            self._access_token = payload["access_token"]
            self._token_expires_at = (
                time.time() + int(payload.get("expires_in", 3600)) - 60
            )
            return self._access_token
        except (httpx.HTTPError, KeyError, ValueError):
            logger.warning("Could not obtain a Logto access token.", exc_info=True)
            return None


def _m2m_configured(settings: Settings) -> bool:
    return bool(
        settings.logto_endpoint
        and settings.logto_api_resource
        and settings.logto_client_id
        and settings.logto_client_secret
    )


async def post_listings(
    combined: dict,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
    token_source: LogtoTokenSource | None = None,
) -> dict | None:
    """POST the agent's combined output to the Repair Lab API.

    Returns the parsed response body on success, or ``None`` when ingestion is
    disabled, credentials are incomplete, or the request fails. Failures are
    logged, never raised, so a network hiccup does not crash the graph.
    """
    if not settings.repair_lab_api_url:
        return None
    if not _m2m_configured(settings):
        logger.warning("Skipping ingest: Logto credentials are incomplete.")
        return None

    owns_client = client is None
    client = client or httpx.AsyncClient()
    token_source = token_source or LogtoTokenSource(
        endpoint=settings.logto_endpoint,
        resource=settings.logto_api_resource,
        client_id=settings.logto_client_id,
        client_secret=settings.logto_client_secret,
        client=client,
    )

    try:
        token = await token_source.get_access_token()
        if token is None:
            return None
        response = await client.post(
            f"{settings.repair_lab_api_url.rstrip('/')}/listings",
            headers={"Authorization": f"Bearer {token}"},
            json=combined,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(
            "Ingested listings: inserted=%s updated=%s total=%s",
            result.get("inserted"),
            result.get("updated"),
            result.get("total"),
        )
        return result
    except (httpx.HTTPError, ValueError):
        logger.warning("Failed to ingest listings into Repair Lab.", exc_info=True)
        return None
    finally:
        if owns_client:
            await client.aclose()
