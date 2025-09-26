"""Agent that brokers knowledge retrieval requests to the RAG pipeline."""
from __future__ import annotations

import logging
from typing import Any

from .models import AgentResult, AgentTask
from ..services.rag_client import RagClient
from ..tools.text_utils import synthesize_answer

logger = logging.getLogger(__name__)


class RagQueryAgent:
    """Handles natural language questions by consulting the RAG service."""

    def __init__(self, rag_client: RagClient) -> None:
        self._rag_client = rag_client

    async def run(self, task: AgentTask, *, top_k: int = 5) -> AgentResult:
        logger.info("agent.start", extra={"task_id": task.task_id, "top_k": top_k})
        snippets = await self._rag_client.fetch_context(task.query, top_k=top_k)
        answer = synthesize_answer(task.query, snippets)
        metadata: dict[str, Any] = {
            "source": "CoE-RagPipeline",
            "snippet_count": len(snippets),
        }
        metadata.update(task.metadata or {})
        logger.info(
            "agent.complete",
            extra={
                "task_id": task.task_id,
                "snippet_count": len(snippets),
            },
        )
        return AgentResult(
            task_id=task.task_id,
            answer=answer,
            context_snippets=snippets,
            metadata=metadata,
        )
