"""Async client for interacting with the CoE-RagPipeline service."""
from __future__ import annotations

import asyncio
from typing import Any, Sequence

import httpx

from core.models import RagSearchResult, RagSourceSummaryResult


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

        results = await self.semantic_search(query=query, k=top_k)
        return [result.as_context() for result in results]

    async def semantic_search(
        self,
        *,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
        analysis_id: str | None = None,
        repository_url: str | None = None,
        group_name: str | None = None,
    ) -> list[RagSearchResult]:
        """Execute a semantic vector search against the pipeline."""

        payload: dict[str, Any] = {"query": query, "k": k}
        if filter_metadata:
            payload["filter_metadata"] = filter_metadata
        if analysis_id:
            payload["analysis_id"] = analysis_id
        if repository_url:
            payload["repository_url"] = repository_url
        if group_name:
            payload["group_name"] = group_name

        body = await self._request_json("POST", "/api/v1/search", json=payload)
        results: list[RagSearchResult] = []
        for entry in body or []:
            results.append(
                RagSearchResult(
                    content=str(entry.get("content", "")),
                    metadata=dict(entry.get("metadata") or {}),
                    original_score=entry.get("original_score"),
                    rerank_score=entry.get("rerank_score"),
                )
            )
        return results

    async def search_source_summaries(
        self,
        *,
        analysis_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[RagSourceSummaryResult]:
        """Search vectorised source summaries for a specific analysis."""

        params = {"query": query, "top_k": top_k}
        body = await self._request_json(
            "GET",
            f"/api/v1/source-summary/search/{analysis_id}",
            params=params,
        )
        data = (body or {}).get("data", {})
        results: list[RagSourceSummaryResult] = []
        for entry in data.get("results", []) or []:
            results.append(
                RagSourceSummaryResult(
                    content=str(entry.get("content", "")),
                    file_path=entry.get("file_path"),
                    language=entry.get("language"),
                    similarity_score=entry.get("similarity_score"),
                    metadata=dict(entry.get("metadata") or {}),
                )
            )
        return results

    async def start_analysis(
        self,
        *,
        repositories: Sequence[dict[str, Any]],
        **options: Any,
    ) -> dict[str, Any]:
        """Kick off a repository analysis workflow."""

        if not repositories:
            raise ValueError("at least one repository is required to start analysis")

        payload: dict[str, Any] = {"repositories": list(repositories)}
        payload.update({k: v for k, v in options.items() if v is not None})
        body = await self._request_json("POST", "/api/v1/analyze", json=payload)
        return body or {}

    async def get_analysis_result(self, analysis_id: str) -> dict[str, Any]:
        """Fetch a previously generated analysis result."""

        return await self._request_json("GET", f"/api/v1/results/{analysis_id}") or {}

    async def list_analysis_results(self) -> list[dict[str, Any]]:
        """List available analysis runs."""

        body = await self._request_json("GET", "/api/v1/results")
        return list(body or [])

    async def generate_documents(
        self,
        *,
        analysis_id: str,
        document_types: Sequence[str],
        language: str = "korean",
        custom_prompt: str | None = None,
        use_source_summaries: bool = True,
    ) -> dict[str, Any]:
        """Request document generation for a particular analysis."""

        if not document_types:
            raise ValueError("document_types must contain at least one entry")

        payload: dict[str, Any] = {
            "analysis_id": analysis_id,
            "document_types": list(document_types),
            "language": language,
        }
        if custom_prompt:
            payload["custom_prompt"] = custom_prompt

        params = {"use_source_summaries": str(bool(use_source_summaries)).lower()}
        body = await self._request_json(
            "POST", "/api/v1/documents/generate", json=payload, params=params
        )
        return body or {}

    async def get_document_status(self, task_id: str) -> dict[str, Any]:
        """Retrieve the status of an asynchronous document generation task."""

        return await self._request_json(
            "GET", f"/api/v1/documents/status/{task_id}"
        ) or {}

    async def list_document_types(self) -> list[str]:
        """List supported document generation types."""

        body = await self._request_json("GET", "/api/v1/documents/types")
        return list(body or [])

    async def get_embedding_stats(self) -> dict[str, Any]:
        """Fetch embedding store statistics."""

        return await self._request_json("GET", "/api/v1/stats") or {}

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an HTTP request and return the decoded JSON payload."""

        url = f"{self._base_url}{path}"
        if self._client is None:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, json=json, params=params)
        else:
            response = await self._client.request(method, url, json=json, params=params)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()


async def warmup_client(rag_client: RagClient) -> None:
    """Ping the backing RAG service to ensure connectivity."""

    try:
        await rag_client.fetch_context("__healthcheck__", top_k=1)
    except httpx.HTTPError:
        # Healthcheck failures surface as noisy logs but do not crash startup.
        await asyncio.sleep(0)
