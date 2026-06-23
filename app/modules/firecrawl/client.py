from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import aiohttp


@dataclass(frozen=True, slots=True)
class FirecrawlUpstreamResponse:
    status: int
    headers: Mapping[str, str]
    json_body: dict[str, object] | None
    text_body: str | None


class FirecrawlClient:
    def __init__(self, base_url: str = "https://api.firecrawl.dev") -> None:
        self._base_url = base_url.rstrip("/")

    async def request(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        json: dict[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> FirecrawlUpstreamResponse:
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
            async with session.request(method, url, headers=headers, json=json, params=params) as response:
                response_headers = dict(response.headers)
                if _is_json_response(response_headers):
                    try:
                        body = await response.json()
                    except aiohttp.ContentTypeError:
                        return FirecrawlUpstreamResponse(
                            status=response.status,
                            headers=response_headers,
                            json_body=None,
                            text_body=await response.text(),
                        )
                    if isinstance(body, dict):
                        return FirecrawlUpstreamResponse(
                            status=response.status,
                            headers=response_headers,
                            json_body=body,
                            text_body=None,
                        )
                return FirecrawlUpstreamResponse(
                    status=response.status,
                    headers=response_headers,
                    json_body=None,
                    text_body=await response.text(),
                )

    async def get_team_credit_usage(self, *, api_key: str) -> FirecrawlUpstreamResponse:
        return await self.request("GET", "/v2/team/credit-usage", api_key=api_key)

    async def get_team_queue_status(self, *, api_key: str) -> FirecrawlUpstreamResponse:
        return await self.request("GET", "/v2/team/queue-status", api_key=api_key)


def _is_json_response(headers: Mapping[str, str]) -> bool:
    content_type = headers.get("content-type") or headers.get("Content-Type") or ""
    return "application/json" in content_type.lower()


def create_firecrawl_client() -> FirecrawlClient:
    return FirecrawlClient()
