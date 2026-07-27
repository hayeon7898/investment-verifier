# agent-behavior.md

`ARCHITECTURE.md`의 "4.2 ~ 4.5 (멀티 에이전트 / ReAct / CoVe / 라우팅)"를 구체화한 문서.
agent-core 패키지 구현은 이 문서를 따른다.

---

## 1. 에이전트 페르소나

### 1.1 공통 규칙
- 세 에이전트 모두 동일한 입력(투자 전략 원문 + 구조화된 파싱 결과)을 받는다
- 각 에이전트는 독립적으로 1차 초안을 생성한 뒤, 다른 두 에이전트의 초안을 보고 반박(rebuttal)을 1회 생성한다
- 모든 주장은 반드시 근거(도구 호출 결과 또는 명시적 가정)를 동반해야 하며, 근거 없는 주장은 하네스 단계에서 거부된다
- 각 에이전트는 자기 관점에 유리한 근거만 선택하지 않도록, 시스템 프롬프트에 "반대 근거도 최소 1개 이상 명시할 것"을 강제한다

### 1.2 Bull 에이전트
- 역할: 전략이 성공할 조건과 근거를 최대한 탐색
- 출력: 상승 논거 목록, 각 논거의 전제 조건, 전제가 깨질 경우의 신호

### 1.3 Bear 에이전트
- 역할: 전략이 실패할 조건과 근거를 최대한 탐색
- 출력: 하락 논거 목록, 각 논거의 전제 조건, 전제가 깨질 경우의 신호

### 1.4 Risk 에이전트
- 역할: Bull/Bear 어느 쪽에도 속하지 않는 구조적 리스크 탐색 (유동성, 변동성, 상관관계 붕괴, 꼬리 위험 등)
- 출력: 리스크 요인 목록, 각 요인의 발생 가능성(정성적: 낮음/중간/높음), 발생 시 영향도

---

## 2. 도구 스키마

모든 도구는 Pydantic 모델로 입출력을 강제한다. 실패 시 1회 재시도 후 폴백(캐시된 최근 값 또는 "데이터 없음" 명시).

### 2.1 `get_price_history`
```
input:  { ticker: str, start_date: date, end_date: date, interval: "1d" | "1wk" | "1mo" }
output: { ticker: str, prices: list[{date: date, close: float}], source: str }
```

### 2.2 `get_macro_indicator`
```
input:  { indicator: "fed_funds_rate" | "cpi" | "unemployment_rate" | ..., start_date: date, end_date: date }
output: { indicator: str, values: list[{date: date, value: float}], source: str }
```

### 2.3 `run_backtest`
```
input:  { condition: str, target_ticker: str, lookback_years: int }
output: { win_rate: float, avg_return: float, sample_size: int, matched_periods: list[{start: date, end: date}] }
```

### 2.4 `search_news`
```
input:  { query: str, date_range: {start: date, end: date} | null }
output: { articles: list[{title: str, summary: str, published_at: date, source: str}] }
```
- 주의: `search_news` 결과는 반드시 "데이터"로 마킹되어 프롬프트에 삽입 (지시로 해석 금지, 프롬프트 인젝션 방어 규칙 적용)

---

## 3. ReAct 루프 정지 조건

- 최대 반복 횟수: 6회 (Thought-Action-Observation 1세트 = 1회)
- 정지 조건 (아래 중 하나라도 만족 시 종료):
  1. 에이전트가 결론에 도달했다고 명시적으로 선언
  2. 최대 반복 횟수 도달 → 이 경우 "불확실성 높음" 플래그를 결과에 강제 포함
  3. 동일 도구를 동일 인자로 2회 연속 호출 시도 (루프 방지)
- 타임아웃: 에이전트 1개당 30초, 초과 시 마지막 관찰까지의 결과로 강제 종료

---

## 4. LLM 라우팅 기준

### 4.1 1차 라우팅 (기본)
- 모든 요청은 경량 모델(Haiku급)로 Bull/Bear/Risk 초안 생성

### 4.2 재라우팅 트리거 (아래 중 하나라도 해당 시 정밀 모델로 재실행)
- Bull과 Bear의 결론 방향이 반대(하나는 긍정적, 하나는 부정적)이면서 각자의 확신도가 모두 중간 이상
- Risk 에이전트가 "높음" 등급 리스크를 1개 이상 도출
- 1차 초안에서 근거 부족으로 하네스가 반려한 주장이 전체의 30% 이상

### 4.3 기록
- 라우팅 판단 근거(트리거 항목, 1차/2차 모델명, 토큰 비용)는 감사 로그에 필수 기록

---

## 5. CoVe 검증 규칙

- 대상: 재라우팅된 케이스에서 신뢰도가 낮게 표시된 핵심 주장 (에이전트당 최대 3개)
- 절차:
  1. 주장에서 검증 가능한 사실 요소 추출
  2. 각 요소에 대한 독립적인 검증 질문 생성
  3. 검증 질문에 대해 원 주장과 무관하게 별도로 답변 (도구 재호출 가능)
  4. 원 주장과 검증 답변이 불일치하면 주장 수정 또는 신뢰도 하향
- 통과율 = (검증 통과 요소 수) / (전체 검증 요소 수), 신뢰도 점수의 입력값으로 사용

---

## 6. 신뢰도 점수 산식 (초안)

```
confidence_score =
    0.4 * self_consistency_rate      # 동일 질문 N=3회 반복 시 결론 일치도
  + 0.4 * cove_pass_rate             # CoVe 검증 통과율 (미적용 시 1.0으로 간주)
  + 0.2 * agent_agreement_rate       # Bull/Bear/Risk 간 부분 합의도
```
- 각 구성 요소는 결과 화면에 분해되어 노출 (Explainable 요구사항 충족)
- 산식은 초안이며, 실측 후 가중치 조정 가능 — 변경 시 이 문서와 ADR 동시 갱신

---

## 7. 관련 문서
- `ARCHITECTURE.md`
- `api-contract.md` (도구의 MCP 인터페이스 노출 방식)