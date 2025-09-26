# Repository Guidelines

프로젝트의 전체 개요와 장기 설계 방향은 `README.md`에 정리되어 있으니, 기여 전 반드시 “디렉터리 구성”과 “A2A 확장 설계안” 섹션을 먼저 확인하세요.

## Project Structure & Module Organization
- `core/models.py`: 공용 데이터 모델과 워크플로 정의.
- `core/agents/`: `RagQueryAgent`, `RagWorkflowAgent` 등 실행 에이전트 구현.
- `services/rag_client.py`: RAG 파이프라인 API를 호출하는 비동기 클라이언트.
- `tools/`: 응답 후처리 유틸. `tests/`: pytest 단위 테스트.
- 상위에 `README.md`, 구현 설계와 로드맵 참고.

## Build, Test, and Development Commands
- `pytest -q`: 전체 단위 테스트 실행.
- `python main.py <query>`: 단일 질의형 에이전트 실행.
- `python main.py --agent workflow --workflow '<json>'`: 워크플로 에이전트 실행.
- RAG 파이프라인이 필요할 경우 `base-url`을 `--base-url http://localhost:8001`처럼 지정.

## Coding Style & Naming Conventions
- Python 3.11, 4 space indentation.
- 모듈/함수는 `snake_case`, 클래스는 `PascalCase`, 유틸은 `_tool.py` 접미사 권장.
- 변경 시 `ruff check CoE-Agent`로 스타일 점검 가능.

## Testing Guidelines
- 프레임워크: `pytest`
- 테스트 파일: `tests/test_*.py`
- 워크플로/클라이언트 시나리오에 대한 고립 테스트(목 객체 활용) 권장.

## Commit & Pull Request Guidelines
- 커밋: Conventional Commits (`feat(agent): ...`, `fix(client): ...`).
- PR: 변경 서비스 명시, 이슈 링크, 실행 방법이나 스크린샷/예제 명령 첨부.
- 설정 변경이나 새 환경 변수가 있으면 문서화 필수.

## Agent-Specific Tips
- 새 에이전트는 `core/agents/`에 추가하고 `core/agents/__init__.py` 레지스트리에 등록.
- 워크플로 DSL은 JSON 배열 기반, `operation` 값은 `core/models.py`의 `RagOperationType` 참고.
- RAG 파이프라인이 외부에 있을 수 있으므로 네트워크 URL을 환경별로 분리 관리.

## Security & Configuration Tips
- 비밀정보는 `.env`로 관리, 저장소에는 포함하지 않음.
- Docker 네트워크 사용 시 `coe-ragpipeline-dev:8001` 같은 서비스 호스트 이용.
- 장기 작업이나 외부 API 호출 시 재시도/타임아웃을 지정해 실패를 흡수.

## Architecture References
- `README.md`: 기본 구조, 워크플로 실행 방법, A2A 확장 설계와 로드맵
- 추가 설계 문서는 `docs/` 디렉터리에 정리하고, 새 파일을 만들면 이 섹션에 링크를 추가하세요.
