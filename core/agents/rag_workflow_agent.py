"""Workflow-oriented agent that composes multiple RAG operations."""
from __future__ import annotations

import logging
from typing import Any, Iterable

from core.models import (
    AgentResult,
    AgentStepResult,
    RagOperationType,
    RagWorkflowStep,
    RagWorkflowTask,
)
from services.rag_client import RagClient
from tools.text_utils import synthesize_answer

logger = logging.getLogger(__name__)


class RagWorkflowAgent:
    """Coordinates multi-step retrieval and analysis workflows."""

    def __init__(self, rag_client: RagClient) -> None:
        self._rag_client = rag_client

    async def run(self, task: RagWorkflowTask) -> AgentResult:
        if not task.operations:
            raise ValueError("workflow task must declare at least one operation")

        logger.info(
            "workflow_agent.start",
            extra={
                "task_id": task.task_id,
                "operations": [step.operation.value for step in task.operations],
            },
        )

        step_results: list[AgentStepResult] = []
        collected_snippets: list[str] = []
        answer_notes: list[str] = []
        metadata: dict[str, Any] = {"workflow_operation_count": len(task.operations)}
        if task.metadata:
            metadata.update(task.metadata)

        for index, step in enumerate(task.operations, start=1):
            try:
                output, snippets, note = await self._execute_step(step=step, task=task)
            except Exception as exc:  # pragma: no cover - defensive logging path
                logger.exception(
                    "workflow_agent.step_failed",
                    extra={"task_id": task.task_id, "operation": step.operation.value},
                )
                step_results.append(
                    AgentStepResult(
                        operation=step.operation.value,
                        status="failed",
                        output={"error": str(exc)},
                    )
                )
                answer_notes.append(
                    f"Step {index} ({step.operation.value}) failed: {exc}"
                )
                continue

            step_results.append(
                AgentStepResult(
                    operation=step.operation.value,
                    status="succeeded",
                    output=output,
                )
            )
            collected_snippets.extend(snippets)
            if note:
                answer_notes.append(f"Step {index} ({step.operation.value}): {note}")

        answer = ""
        if task.query and collected_snippets:
            answer = synthesize_answer(task.query, collected_snippets)
        if not answer and answer_notes:
            answer = "\n".join(answer_notes)
        if not answer:
            answer = "Workflow completed without textual output."

        logger.info(
            "workflow_agent.complete",
            extra={
                "task_id": task.task_id,
                "step_count": len(step_results),
            },
        )

        return AgentResult(
            task_id=task.task_id,
            answer=answer,
            context_snippets=collected_snippets,
            metadata=metadata,
            steps=step_results,
        )

    async def _execute_step(
        self,
        *,
        step: RagWorkflowStep,
        task: RagWorkflowTask,
    ) -> tuple[Any, list[str], str]:
        """Dispatch a single workflow step."""

        operation = step.operation
        params = step.parameters

        if operation is RagOperationType.SEMANTIC_SEARCH:
            return await self._semantic_search_step(params=params, task=task)
        if operation is RagOperationType.SOURCE_SUMMARY_SEARCH:
            return await self._source_summary_step(params=params, task=task)
        if operation is RagOperationType.START_ANALYSIS:
            return await self._start_analysis_step(params=params)
        if operation is RagOperationType.GET_ANALYSIS_RESULT:
            return await self._get_analysis_result_step(params=params)
        if operation is RagOperationType.LIST_ANALYSIS_RESULTS:
            return await self._list_analysis_results_step()
        if operation is RagOperationType.GENERATE_DOCUMENTS:
            return await self._generate_documents_step(params=params)
        if operation is RagOperationType.GET_DOCUMENT_STATUS:
            return await self._get_document_status_step(params=params)
        if operation is RagOperationType.EMBEDDING_STATS:
            return await self._embedding_stats_step()

        raise ValueError(f"Unsupported workflow operation: {operation}")

    async def _semantic_search_step(
        self,
        *,
        params: dict[str, Any],
        task: RagWorkflowTask,
    ) -> tuple[list[dict[str, Any]], list[str], str]:
        query = params.get("query") or task.query
        if not query:
            raise ValueError("semantic_search requires a query")

        results = await self._rag_client.semantic_search(
            query=query,
            k=int(params.get("k", params.get("top_k", 5))),
            filter_metadata=params.get("filter_metadata"),
            analysis_id=params.get("analysis_id"),
            repository_url=params.get("repository_url"),
            group_name=params.get("group_name"),
        )
        snippets = [entry.as_context() for entry in results]
        output = [
            {
                "content": entry.content,
                "metadata": entry.metadata,
                "original_score": entry.original_score,
                "rerank_score": entry.rerank_score,
            }
            for entry in results
        ]
        note = f"retrieved {len(output)} semantic matches"
        return output, snippets, note

    async def _source_summary_step(
        self,
        *,
        params: dict[str, Any],
        task: RagWorkflowTask,
    ) -> tuple[list[dict[str, Any]], list[str], str]:
        analysis_id = params.get("analysis_id")
        if not analysis_id:
            raise ValueError("source_summary_search requires analysis_id")
        query = params.get("query") or task.query
        if not query:
            raise ValueError("source_summary_search requires a query")

        results = await self._rag_client.search_source_summaries(
            analysis_id=analysis_id,
            query=query,
            top_k=int(params.get("top_k", params.get("k", 10))),
        )
        snippets = [entry.as_context() for entry in results]
        output = [
            {
                "content": entry.content,
                "file_path": entry.file_path,
                "language": entry.language,
                "similarity_score": entry.similarity_score,
                "metadata": entry.metadata,
            }
            for entry in results
        ]
        note = f"retrieved {len(output)} source summaries for analysis {analysis_id}"
        return output, snippets, note

    async def _start_analysis_step(
        self,
        *,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], str]:
        repositories = params.get("repositories")
        if not repositories:
            raise ValueError("start_analysis requires repositories")

        options = {key: value for key, value in params.items() if key != "repositories"}
        result = await self._rag_client.start_analysis(
            repositories=repositories,
            **options,
        )
        note = f"analysis started with id {result.get('analysis_id', 'unknown')}"
        return result, [], note

    async def _get_analysis_result_step(
        self,
        *,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], str]:
        analysis_id = params.get("analysis_id")
        if not analysis_id:
            raise ValueError("get_analysis_result requires analysis_id")

        result = await self._rag_client.get_analysis_result(analysis_id)
        snippets = list(self._extract_repository_headlines(result))
        note = f"analysis {analysis_id} status {result.get('status', 'unknown')}"
        return result, snippets, note

    async def _list_analysis_results_step(self) -> tuple[list[dict[str, Any]], list[str], str]:
        results = await self._rag_client.list_analysis_results()
        note = f"found {len(results)} recorded analyses"
        return results, [], note

    async def _generate_documents_step(
        self,
        *,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], str]:
        analysis_id = params.get("analysis_id")
        document_types = params.get("document_types")
        if not analysis_id or not document_types:
            raise ValueError("generate_documents requires analysis_id and document_types")

        result = await self._rag_client.generate_documents(
            analysis_id=analysis_id,
            document_types=document_types,
            language=params.get("language", "korean"),
            custom_prompt=params.get("custom_prompt"),
            use_source_summaries=params.get("use_source_summaries", True),
        )
        note = f"document generation task {result.get('task_id', 'unknown')} submitted"
        return result, [], note

    async def _get_document_status_step(
        self,
        *,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], str]:
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("get_document_status requires task_id")

        result = await self._rag_client.get_document_status(task_id)
        note = f"document task {task_id} status {result.get('status', 'unknown')}"
        return result, [], note

    async def _embedding_stats_step(self) -> tuple[dict[str, Any], list[str], str]:
        result = await self._rag_client.get_embedding_stats()
        note = "retrieved embedding statistics"
        return result, [], note

    @staticmethod
    def _extract_repository_headlines(analysis_result: dict[str, Any]) -> Iterable[str]:
        repositories = analysis_result.get("repositories") or []
        if not repositories:
            return []
        headlines: list[str] = []
        for repo in repositories[:3]:
            repo_name = RagWorkflowAgent._safe_get(repo, "name") or RagWorkflowAgent._safe_get(repo, "url") or "unknown"
            language = RagWorkflowAgent._safe_get(repo, "primary_language") or RagWorkflowAgent._safe_get(repo, "language")
            headline = repo_name
            if language:
                headline = f"{headline} ({language})"
            headlines.append(f"Repository insight: {headline}")
        return headlines

    @staticmethod
    def _safe_get(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)
