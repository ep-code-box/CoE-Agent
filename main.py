"""Entrypoint for running the CoE rag query agent as a CLI."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from dataclasses import asdict
from typing import Any

from core.agents import AGENT_REGISTRY, RagQueryAgent, RagWorkflowAgent
from core.models import (
    AgentTask,
    RagOperationType,
    RagWorkflowStep,
    RagWorkflowTask,
)
from services.rag_client import RagClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


AGENT_CHOICES = tuple(AGENT_REGISTRY.keys())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CoE rag agent")
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Natural language question or prompt (required for query agent)",
    )
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
    parser.add_argument(
        "--agent",
        choices=AGENT_CHOICES,
        default="query",
        help="Agent mode to execute",
    )
    parser.add_argument(
        "--workflow",
        help="Workflow definition as JSON array when running the workflow agent",
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="Guide agent profile name",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="File paths to provide as context for the guide agent",
    )
    parser.add_argument(
        "--language",
        choices=("ko", "en"),
        default="ko",
        help="Preferred language for guide agent responses",
    )
    return parser


async def run_cli() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.agent == "guide":
        if args.query is None:
            parser.error("guide agent requires a query prompt")
        guide_cls = AGENT_REGISTRY["guide"]
        async with RagClient(args.base_url) as rag_client:
            guide_agent = guide_cls(rag_client=rag_client)  # type: ignore[call-arg]
            result = await guide_agent.run(
                prompt=args.query,
                profile=args.profile,
                language=args.language,
                paths=args.paths or (),
            )
        payload = {
            "summary": result.summary,
            "plan": list(result.plan),
            "insights": list(result.insights),
            "recommendations": [asdict(rec) for rec in result.recommendations],
            "memory": asdict(result.memory),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    async with RagClient(args.base_url) as rag_client:
        if args.agent == "workflow":
            operations = _parse_workflow_definition(args.workflow)
            workflow_task = RagWorkflowTask(
                task_id=str(uuid.uuid4()),
                query=args.query,
                operations=operations,
            )
            agent = RagWorkflowAgent(rag_client)
            result = await agent.run(workflow_task)
        else:
            if args.query is None:
                parser.error("query argument is required when using the query agent")
            task = AgentTask(task_id=str(uuid.uuid4()), query=args.query)
            agent = RagQueryAgent(rag_client)
            result = await agent.run(task, top_k=args.top_k)

    payload = {
        "task_id": result.task_id,
        "answer": result.answer,
        "context_snippets": result.context_snippets,
        "metadata": result.metadata,
    }
    if result.steps is not None:
        payload["steps"] = [
            {
                "operation": step.operation,
                "status": step.status,
                "output": step.output,
            }
            for step in result.steps
        ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _parse_workflow_definition(raw_json: str | None) -> list[RagWorkflowStep]:
    if not raw_json:
        raise SystemExit("workflow agent requires --workflow JSON definition")

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - argparse validation
        raise SystemExit(f"Failed to parse workflow JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise SystemExit("Workflow definition must be a JSON array of steps")

    steps: list[RagWorkflowStep] = []
    for index, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise SystemExit(f"Workflow step #{index + 1} must be a JSON object")
        operation = entry.get("operation")
        if not isinstance(operation, str):
            raise SystemExit(f"Workflow step #{index + 1} is missing 'operation'")
        try:
            op_enum = RagOperationType(operation)
        except ValueError as exc:
            raise SystemExit(
                f"Unsupported workflow operation '{operation}' at step #{index + 1}"
            ) from exc

        parameters: dict[str, Any] = entry.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise SystemExit(f"Workflow step #{index + 1} parameters must be an object")

        steps.append(RagWorkflowStep(operation=op_enum, parameters=parameters))

    return steps


def main() -> None:
    try:
        exit_code = asyncio.run(run_cli())
    except KeyboardInterrupt:
        print("Execution cancelled", file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
