"""Shared data models used across the CoE-Agent service."""
from dataclasses import dataclass
from typing import Any


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
    context_snippets: list[str]
    metadata: dict[str, Any] | None = None
