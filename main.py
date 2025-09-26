"""Entrypoint for running the CoE rag query agent as a CLI."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid

from core.models import AgentTask
from core.rag_query_agent import RagQueryAgent
from services.rag_client import RagClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CoE rag query agent")
    parser.add_argument("query", help="Natural language question or prompt")
    parser.add_argument(
        "--base-url",
        default="http://coe-ragpipeline-dev:8001",
        help="Base URL for the RAG service",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of snippets to retrieve",
    )
    return parser


async def run_cli() -> int:
    parser = build_parser()
    args = parser.parse_args()

    task = AgentTask(task_id=str(uuid.uuid4()), query=args.query)

    async with RagClient(args.base_url) as rag_client:
        agent = RagQueryAgent(rag_client)
        result = await agent.run(task, top_k=args.top_k)

    payload = {
        "task_id": result.task_id,
        "answer": result.answer,
        "context_snippets": result.context_snippets,
        "metadata": result.metadata,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    try:
        exit_code = asyncio.run(run_cli())
    except KeyboardInterrupt:
        print("Execution cancelled", file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
