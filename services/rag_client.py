"""Async client for interacting with the CoE-RagPipeline service."""
from __future__ import annotations

import asyncio
from typing import Any, Sequence

import httpx


class RagClient:
    """Fetches supporting documents from the RAG pipeline."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client

    async def __aenter__(self) -> "RagClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def fetch_context(self, query: str, *, top_k: int = 5) -> list[str]:
        """Retrieve top-K context snippets relevant to the query."""

        if self._client is None:
            # Lazily create a short-lived client when used without context manager.
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await self._request_context(client, query=query, top_k=top_k)
        return await self._request_context(self._client, query=query, top_k=top_k)

    async def _request_context(
        self,
        client: httpx.AsyncClient,
        *,
        query: str,
        top_k: int,
    ) -> list[str]:
        payload = {"query": query, "top_k": top_k}
        response = await client.post(f"{self._base_url}/query", json=payload)
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        snippets: Sequence[str] = body.get("snippets", [])
        return list(snippets)


async def warmup_client(rag_client: RagClient) -> None:
    """Ping the backing RAG service to ensure connectivity."""

    try:
        await rag_client.fetch_context("__healthcheck__", top_k=1)
    except httpx.HTTPError:
        # Healthcheck failures surface as noisy logs but do not crash startup.
        await asyncio.sleep(0)
