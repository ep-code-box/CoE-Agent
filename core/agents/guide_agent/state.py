"""State structures shared across the guide agent LangGraph."""
from __future__ import annotations

from typing import Any, List

from typing_extensions import TypedDict

from core.models import DeveloperContext, GuidanceRecommendation, SessionMemory


class GuideAgentState(TypedDict, total=False):
    """Aggregated state flowing through the guide agent graph."""

    context: DeveloperContext
    memory: SessionMemory
    plan: List[str]
    insights: List[str]
    recommendations: List[GuidanceRecommendation]
    raw_request: dict[str, Any]
    summary: str
    rag_client: Any
