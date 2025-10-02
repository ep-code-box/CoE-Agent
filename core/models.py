"""Shared data models used across the CoE-Agent service."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Sequence


@dataclass(slots=True)
class AgentTask:
    """Represents a single unit of work the agent must execute."""

    task_id: str
    query: str
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class AgentResult:
    """Captures the outcome returned by an agent run."""

    task_id: str
    answer: str
    context_snippets: list[str] = field(default_factory=list)
    metadata: dict[str, Any] | None = None
    steps: Sequence["AgentStepResult"] | None = None


@dataclass(slots=True)
class DeveloperContext:
    """Captures the execution backdrop for guide-style agents."""

    profile_name: str
    working_paths: tuple[str, ...] = ()
    target_branch: str | None = None
    language: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class GuidanceRecommendation:
    """Represents a single actionable suggestion for the developer."""

    title: str
    detail: str
    rationale: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    priority: Literal["high", "medium", "low"] = "medium"
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class SessionMemory:
    """Lightweight session memory shared between guide agent nodes."""

    session_id: str
    recent_summary: str = ""
    acknowledged_recommendations: tuple[str, ...] = ()
    pending_questions: tuple[str, ...] = ()
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GuideAgentResult:
    """Aggregated response returned by the guide agent."""

    summary: str
    plan: Sequence[str]
    recommendations: Sequence[GuidanceRecommendation]
    insights: Sequence[str]
    memory: SessionMemory


class RagOperationType(StrEnum):
    """Supported operation types for orchestrating RAG workflows."""

    SEMANTIC_SEARCH = "semantic_search"
    SOURCE_SUMMARY_SEARCH = "source_summary_search"
    START_ANALYSIS = "start_analysis"
    GET_ANALYSIS_RESULT = "get_analysis_result"
    LIST_ANALYSIS_RESULTS = "list_analysis_results"
    GENERATE_DOCUMENTS = "generate_documents"
    GET_DOCUMENT_STATUS = "get_document_status"
    EMBEDDING_STATS = "embedding_stats"


@dataclass(slots=True)
class RagWorkflowStep:
    """Single step definition in a RAG workflow."""

    operation: RagOperationType
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RagWorkflowTask:
    """Composite task composed of one or more workflow steps."""

    task_id: str
    query: str | None = None
    operations: list[RagWorkflowStep] = field(default_factory=list)
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class AgentStepResult:
    """Outcome for an individual workflow step."""

    operation: str
    status: str
    output: Any


@dataclass(slots=True)
class RagSearchResult:
    """Structured representation of a semantic search hit."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    original_score: float | None = None
    rerank_score: float | None = None

    def as_context(self) -> str:
        """Format the search result as a concise context snippet."""

        label = (
            self.metadata.get("file_name")
            or self.metadata.get("file_path")
            or self.metadata.get("document_type")
            or self.metadata.get("analysis_id")
        )
        prefix = f"[{label}] " if label else ""
        return f"{prefix}{self.content}".strip()


@dataclass(slots=True)
class RagSourceSummaryResult:
    """Structured representation of a source summary search hit."""

    content: str
    file_path: str | None = None
    language: str | None = None
    similarity_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_context(self) -> str:
        """Format the source summary result for downstream synthesis."""

        prefix_parts: list[str] = []
        if self.file_path:
            prefix_parts.append(self.file_path)
        if self.language:
            prefix_parts.append(self.language)
        prefix = " | ".join(prefix_parts)
        if prefix:
            prefix = f"[{prefix}] "
        return f"{prefix}{self.content}".strip()
