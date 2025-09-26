# CoE-Agent

`CoE-Agent` is an experimental workspace for agent components within the CoE repository. The initial implementation, `RagQueryAgent`, accepts a natural language question, retrieves context from the `CoE-RagPipeline`, and synthesizes a concise answer.

## Layout
- `core/`: Agent logic and shared data models.
- `services/`: Clients for communicating with external services.
- `tools/`: Text post-processing and other utilities.
- `main.py`: CLI entry point for manual execution.

## Quickstart
```bash
python CoE-Agent/main.py "What is the agent architecture?" --base-url http://localhost:8001
```

## Next Ideas
1. Extend `RagClient` with authentication, retries, and streaming support.
2. Add coordinator agents that schedule multi-step tasks across backend and RAG services.
3. Cover end-to-end agent scenarios with integration tests.
