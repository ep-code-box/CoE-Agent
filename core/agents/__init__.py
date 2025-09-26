"""Agent implementations and registration utilities."""
from __future__ import annotations

from typing import Callable

from .rag_query_agent import RagQueryAgent
from .rag_workflow_agent import RagWorkflowAgent

AgentFactory = Callable[..., object]

# Simple registry so new agents can be plugged in quickly.
AGENT_REGISTRY: dict[str, AgentFactory] = {
    "query": RagQueryAgent,
    "workflow": RagWorkflowAgent,
}

__all__ = [
    "RagQueryAgent",
    "RagWorkflowAgent",
    "AGENT_REGISTRY",
    "AgentFactory",
]
