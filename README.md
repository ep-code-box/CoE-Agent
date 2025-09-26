# CoE-Agent

`CoE-Agent`는 CoE 저장소 내에서 다양한 에이전트 컴포넌트를 실험하는 워크스페이스입니다. 현재 두 가지 에이전트를 기본으로 제공합니다.

- `RagQueryAgent`: 자연어 질의를 받아 `CoE-RagPipeline`에서 문맥을 검색하고 응답을 요약합니다.
- `RagWorkflowAgent`: 분석, 시맨틱 검색, 문서 생성 등 다단계 RAG 워크플로를 오케스트레이션합니다.

## 디렉터리 구성
- `core/`: 공통 데이터 모델과 에이전트 레지스트리 유틸을 포함합니다.
- `core/agents/`: 개별 에이전트 구현(`RagQueryAgent`, `RagWorkflowAgent` 등)이 위치합니다.
- `services/`: 외부 서비스와 통신하는 클라이언트를 모아둔 공간입니다.
- `tools/`: 텍스트 후처리 등 공용 유틸리티를 제공합니다.
- `main.py`: CLI 실행 진입점입니다.

## 빠르게 사용해보기

단일 질의형 에이전트 실행:

```bash
python CoE-Agent/main.py "What is the agent architecture?" --base-url http://localhost:8001
```

시맨틱 검색 후 임베딩 통계를 조회하는 워크플로 실행:

```bash
python CoE-Agent/main.py \
  --agent workflow \
  --workflow '[
    {"operation": "semantic_search", "parameters": {"query": "FastAPI architecture", "k": 3}},
    {"operation": "embedding_stats"}
  ]'
```

> 워크플로 모드는 단계별 실행 결과를 구조화된 JSON으로 함께 출력해 후속 시스템 연동이 수월합니다.

## 다음 개선 아이디어
1. `RagClient`에 인증, 재시도, 스트리밍 기능을 추가합니다.
2. 백엔드와 RAG 서비스를 아우르는 다단계 작업 스케줄러(코디네이터 에이전트)를 도입합니다.
3. 에이전트 엔드 투 엔드 시나리오에 대한 통합 테스트를 구축합니다.

## A2A 확장 설계안
- **레이어 구조**
  - *Executor Agents*: `RagQueryAgent`, `RagWorkflowAgent`처럼 개별 도메인 작업을 수행하는 실행 단위
  - *Coordinator Agent*: Executor 실행 순서를 조율하고 상태/재시도를 관리하는 오케스트레이션 역할
  - *Supervisor/Planner*: 상위 목표를 분석해 실행할 워크플로를 선택하고 DSL 기반 플랜을 생성
- **메시지/컨텍스트 흐름**
  - 표준화된 메시지 포맷(`task_id`, `agent`, `payload`, `status`)으로 통신
  - 메시지 브로커(Redis Streams/NATS/Kafka 등)에 `tasks`, `events`, `logs` 채널을 구성해 비동기 연결
  - 공용 컨텍스트 저장소에 작업 상태와 중간 산출물을 기록해 에이전트 간 공유
- **워크플로 DSL**
  - YAML/JSON 기반 DSL로 단계, 의존성, 조건을 선언하고 Coordinator가 이를 실행
  - 동적 브랜치/조건 실행을 지원해 예외를 처리
- **런타임 컴포넌트**
  - FastAPI 게이트웨이로 외부 요청을 수집하고, 백그라운드 워커(에이전트)들은 메시지 큐를 구독해 작업 수행
  - 스케줄러/재시도 관리자로 장기 작업과 실패 복구를 담당
- **관찰성과 거버넌스**
  - OpenTelemetry 기반 추적·로그·메트릭 수집, Grafana/Tempo 대시보드 연계
  - Rate limiting, RBAC, 감사 로그 등 운영 정책 반영
- **확장 전략**
  - 에이전트 등록 시 메타데이터(필요 자원, 실패 정책)를 제공해 자동 배치/확장을 지원
  - K8s HPA, Ray Serve 등의 오케스트레이터로 워커 스케일 조정

## 구현 로드맵 (초안)
1. Coordinator/Supervisor 에이전트 스펙 정의 및 레지스트리 연동 구조 마련
2. 메시지 브로커 초안 도입(예: Redis Streams)과 표준 메시지 포맷 적용
3. 워크플로 DSL 스키마 설계 후 Planner→Coordinator 실행 플로우 프로토타입 작성
4. 관찰성 파이프라인(OpenTelemetry + Grafana) 연동 및 기초 대시보드 구축
5. 보안/거버넌스 정책(RBAC, rate limit) 수립과 Gatekeeper 미들웨어 구현
