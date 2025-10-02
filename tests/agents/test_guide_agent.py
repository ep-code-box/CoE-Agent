import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agents.guide_agent.agent import GuideAgent
from core.models import RagSearchResult


def test_guide_agent_generates_recommendations(tmp_path):
    agent = GuideAgent()
    sample_file = tmp_path / "example.py"
    sample_file.write_text("print('hello world')\n", encoding="utf-8")

    result = asyncio.run(
        agent.run(
            prompt="테스트 커버리지를 높이려면?",
            paths=(str(sample_file),),
        )
    )

    assert result.plan, "계획이 비어 있으면 안 됩니다."
    assert result.recommendations, "권장 사항이 생성되어야 합니다."
    assert any("문서" in rec.detail or "가이드" in rec.detail for rec in result.recommendations)
    assert result.summary


def test_guide_agent_with_rag_client_injects_insights():
    class FakeRagClient:
        async def semantic_search(self, *, query: str, k: int = 5, **_: object):
            return [
                RagSearchResult(
                    content=f"{query} 관련 테스트 케이스 작성",
                    metadata={"file_path": "tests/test_example.py"},
                    original_score=0.9,
                    rerank_score=None,
                )
            ]

    agent = GuideAgent(rag_client=FakeRagClient())
    result = asyncio.run(agent.run(prompt="테스트 보강"))

    assert any("테스트" in insight for insight in result.insights)
