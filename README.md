# CoE-Agent

`CoE-Agent` is an experimental workspace for agent components within the CoE repository. The project now ships with two complementary agents:

- `RagQueryAgent`: accepts a natural language question, retrieves context from the `CoE-RagPipeline`, and synthesizes a concise answer.
- `RagWorkflowAgent`: orchestrates multi-step RAG workflows (analysis, semantic search, document generation, etc.) through the pipeline.

## Layout
- `core/`: Shared data models and agent registry helpers.
- `core/agents/`: Individual agent implementations (query, workflow, ...).
- `services/`: Clients for communicating with external services.
- `tools/`: Text post-processing and other utilities.
- `main.py`: CLI entry point for manual execution.

## Quickstart

Run the classic single-step query agent:

```bash
python CoE-Agent/main.py "What is the agent architecture?" --base-url http://localhost:8001
```

Execute a workflow that first performs semantic search and then reports embedding statistics:

```bash
python CoE-Agent/main.py \
  --agent workflow \
  --workflow '[
    {"operation": "semantic_search", "parameters": {"query": "FastAPI architecture", "k": 3}},
    {"operation": "embedding_stats"}
  ]'
```

> Workflows emit structured step-by-step output in addition to the synthesized answer, making it easier to pipe results into other systems.

## Next Ideas
1. Extend `RagClient` with authentication, retries, and streaming support.
2. Add coordinator agents that schedule multi-step tasks across backend and RAG services.
3. Cover end-to-end agent scenarios with integration tests.
