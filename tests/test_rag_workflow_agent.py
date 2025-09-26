import asyncio
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import core.models as core_models

import importlib.util

main_spec = importlib.util.spec_from_file_location(
    "coe_agent_main", PROJECT_ROOT / "main.py"
)
assert main_spec and main_spec.loader
main_module = importlib.util.module_from_spec(main_spec)
sys.modules[main_spec.name] = main_module
main_spec.loader.exec_module(main_module)

RagOperationType = core_models.RagOperationType
RagSearchResult = core_models.RagSearchResult
RagWorkflowStep = core_models.RagWorkflowStep
RagWorkflowTask = core_models.RagWorkflowTask

from core.agents.rag_workflow_agent import RagWorkflowAgent
from services.rag_client import RagClient

_parse_workflow_definition = main_module._parse_workflow_definition


class StubRagClient:
    def __init__(self, *, search_results: list[RagSearchResult]):
        self._search_results = search_results
        self.semantic_calls: list[dict[str, object]] = []

    async def semantic_search(self, **kwargs):
        self.semantic_calls.append(kwargs)
        return self._search_results


def test_workflow_agent_semantic_search_only():
    search_results = [
        RagSearchResult(
            content="FastAPI leverages Starlette for async IO.",
            metadata={"file_name": "architecture.md"},
            original_score=0.92,
            rerank_score=0.88,
        )
    ]
    stub_client = StubRagClient(search_results=search_results)
    agent = RagWorkflowAgent(stub_client)  # type: ignore[arg-type]

    task = RagWorkflowTask(
        task_id="task-1",
        query="How does FastAPI handle async?",
        operations=[
            RagWorkflowStep(
                operation=RagOperationType.SEMANTIC_SEARCH,
                parameters={"query": "FastAPI async architecture", "k": 1},
            )
        ],
    )

    result = asyncio.run(agent.run(task))

    assert result.steps is not None
    assert result.steps[0].operation == RagOperationType.SEMANTIC_SEARCH.value
    assert result.context_snippets
    assert "FastAPI" in result.answer
    assert stub_client.semantic_calls[0]["query"] == "FastAPI async architecture"


def test_parse_workflow_definition_valid():
    workflow_json = json.dumps(
        [
            {
                "operation": RagOperationType.SEMANTIC_SEARCH.value,
                "parameters": {"query": "fastapi"},
            },
            {"operation": RagOperationType.EMBEDDING_STATS.value},
        ]
    )

    steps = _parse_workflow_definition(workflow_json)

    assert len(steps) == 2
    assert steps[0].operation == RagOperationType.SEMANTIC_SEARCH
    assert steps[1].operation == RagOperationType.EMBEDDING_STATS


def test_rag_client_semantic_search_uses_vector_endpoint():
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        payload = json.loads(request.content.decode())
        captured["payload"] = payload
        return httpx.Response(
            200,
            json=[
                {
                    "content": "Example content",
                    "metadata": {"file_name": "README.md"},
                    "original_score": 0.42,
                    "rerank_score": 0.4,
                }
            ],
        )

    async def run_request():
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport)
        async with RagClient("http://example.com", client=http_client) as client:
            return await client.semantic_search(query="hello", k=7, group_name="demo")

    results = asyncio.run(run_request())

    assert captured["method"] == "POST"
    assert str(captured["url"]).endswith("/api/v1/search")
    payload = captured["payload"]
    assert payload["query"] == "hello"
    assert payload["k"] == 7
    assert payload["group_name"] == "demo"
    assert results[0].metadata["file_name"] == "README.md"
