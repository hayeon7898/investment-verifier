# Investment Verifier

투자 전략이나 아이디어를 입력하면 AI가 다각적 관점(Bull / Bear / Risk)에서
근거를 검증하고 리스크를 분석하여 의사결정을 지원하는 Explainable AI 시스템.

---

## 핵심 특징

- **멀티 에이전트 토론**: Bull / Bear / Risk 세 관점이 서로 근거를 반박·검증
- **ReAct 기반 근거 탐색**: 정적 검색이 아니라 상황에 따라 도구(시세 조회, 매크로 지표, 백테스트)를 선택적으로 호출
- **Chain-of-Verification**: 핵심 주장에 대해 독립적인 검증 질문을 생성해 재확인
- **GraphRAG 기반 설명**: 근거 간 인과 관계를 그래프로 구성해 판단 과정을 추적 가능하게 표현
- **LLM 라우팅**: 에이전트 간 의견 불일치도에 따라 경량/정밀 모델을 동적으로 선택
- **감사 로그 + Human-in-the-loop**: 모든 모델·도구 호출을 기록하고, 최종 결과는 사람의 승인을 거쳐 공개

---

## 프로젝트 구조

```
investment-verifier/
├── specs/           # 설계 spec docs
├── packages/
│   └── agent-core/  # ReAct loop, tools, harness, routing, CoVe, GraphRAG
├── backend/         # FastAPI
├── frontend/        # React
└── infra/           # docker-compose 등
```

## 개발 문서

- [`specs/ARCHITECTURE.md`](./specs/ARCHITECTURE.md) — 전체 시스템 구조
- [`specs/agent-behavior.md`](./specs/agent-behavior.md) — 에이전트 역할, 도구 스키마, 라우팅/정지 조건
- `specs/api-contract.md` — API / MCP 도구 명세

구조 변경 시 `specs/` 문서를 먼저 갱신한 뒤 코드에 반영합니다.


---

## 실행 방법


## 기술 스택