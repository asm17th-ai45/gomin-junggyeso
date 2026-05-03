# AGENTS.md — 고민중계소 개발 에이전트 스킬

이 문서는 AI 코딩 에이전트, 팀원, 리뷰어가 고민중계소 레포지토리에서 일할 때 따라야 하는 작업 규칙입니다.

## 1. 프로젝트 목표

고민중계소는 사용자의 고민을 입력받아 서로 다른 관점의 AI Agent들이 토론하고, Judge Agent가 최종 추천 결론을 제시하는 멀티 에이전트 의사결정 지원 서비스입니다.

에이전트가 구현해야 하는 최종 사용자 경험은 다음 한 문장으로 요약됩니다.

> 사용자가 고민을 입력하면 현실주의자·이상주의자·리스크 회피형 Agent가 2라운드 토론을 진행하고, Judge가 결론·이유 3가지·리스크를 구조화해 반환한다.

## 2. 프로젝트 구현 방향

고민중계소는 처음부터 멀티 에이전트 토론 서비스로 구현합니다. 모든 코드는 사용자의 고민을 구조화하고, 서로 다른 관점의 Debater가 토론한 뒤, Judge가 실행 가능한 결론을 반환하는 흐름에 맞춥니다.

구현 기준은 다음과 같습니다.

| 영역 | 구현 기준 |
|---|---|
| 입력 처리 | 사용자 고민에서 선택지, 배경 정보, 판단 기준을 추출 |
| 토론 흐름 | Moderator가 라운드를 관리하고 3개 Debater가 순차 발언 |
| 판단 관점 | 현실주의자·이상주의자·리스크 회피형 관점을 명확히 분리 |
| 최종 출력 | Judge가 결론, 이유 3가지, 리스크, 다음 행동을 구조화해 반환 |
| 확장 기능 | RAG, 장기 메모리, 재토론은 MVP 이후 확장 포인트로만 관리 |

작업 시 파일명이나 함수명보다 역할과 입출력 스키마가 더 중요합니다. 새로 작성하는 모듈은 DebateGraph의 상태 흐름과 API 응답 형식에 맞아야 합니다.

## 3. 필수 구현 범위

### 3-1. Agent

반드시 포함할 Agent는 다음 5개입니다.

1. `Moderator`
   - 사용자 고민을 정리합니다.
   - 선택지, 배경 정보, 판단 기준을 추출합니다.
   - 토론 라운드 시작과 종료 조건을 관리합니다.
   - 입력이 부족하면 토론을 시작하지 않고 핵심 질문 1~2개를 반환합니다.

2. `Realist Debater`
   - 실현 가능성, 현재 제약, 단기 비용/수익 중심으로 판단합니다.
   - 말투는 단정적이고 현실적이어야 합니다.
   - 추측 대신 사용자가 제공한 정보에 기반합니다.

3. `Idealist Debater`
   - 장기 가치, 자기 성장, 의미, 만족도 중심으로 판단합니다.
   - 말투는 설득력 있고 가치 중심이어야 합니다.
   - 현실적 제약을 무시하지 않되 성장 가능성을 적극적으로 검토합니다.

4. `Risk-Averse Debater`
   - 최악의 시나리오, 회복 가능성, 안정성 중심으로 판단합니다.
   - 말투는 신중하고 리스크 관리 중심이어야 합니다.
   - 위험만 나열하지 말고 완화 전략도 제시합니다.

5. `Judge / Synthesizer`
   - 토론 로그를 종합해 최종 결론을 냅니다.
   - 반드시 구조화된 출력으로 반환합니다.
   - 결론은 모호한 양비론이 아니라 실행 가능한 추천이어야 합니다.

### 3-2. MVP 제외 기능

아래 기능은 현재 MVP에서 구현하지 않습니다. 필요한 경우 TODO 또는 확장 포인트로만 남깁니다.

- 사용자 계정/로그인
- 장기 메모리
- 실제 외부 데이터 RAG
- 4번째 도전자 Agent
- 재토론/관점 추가
- 모바일 전용 UI
- 음성 입력
- 결론 공유 기능

## 4. 권장 파일 구조

```text
app/
├── agents/
│   ├── debaters.py
│   ├── moderator.py
│   ├── judge.py
│   └── safety.py
├── core/
│   ├── config.py
│   └── llm.py
├── prompts/
│   ├── debaters.py
│   ├── moderator.py
│   └── judge.py
├── api.py
├── graph.py
├── main.py
└── schemas.py
frontend/
└── ui.py
```

## 5. 데이터 모델 규칙

`app/schemas.py`에는 최소한 다음 모델을 둡니다.

```python
class DebateTurn(BaseModel):
    round: int
    agent: Literal["realist", "idealist", "risk_averse", "moderator"]
    stance: str
    content: str
    target: str | None = None

class FinalDecision(BaseModel):
    recommendation: str
    reasons: list[str]
    risks: list[str]
    next_action: str | None = None

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    query: str
    normalized_problem: dict
    debate_log: list[dict]
    round: int
    max_rounds: int
    final_decision: dict
    safety_status: str
    needs_clarification: bool
    clarification_questions: list[str]
```

규칙:

- `final_decision`은 항상 `recommendation`, `reasons`, `risks`를 포함해야 합니다.
- `reasons`는 정확히 3개를 목표로 합니다.
- `risks`는 최소 1개 이상이어야 합니다.
- `debate_log`는 프론트엔드에서 Agent별 메시지로 렌더링 가능해야 합니다.

## 6. LangGraph 구현 규칙

`app/graph.py`는 DebateGraph의 단일 진입점을 제공합니다.

권장 흐름:

```text
START
  → safety_check
  → moderator
  → realist
  → idealist
  → risk_averse
  → round_check
      ├─ continue → realist
      └─ finish → judge
  → END
```

구현 원칙:

- 라운드 반복은 `add_conditional_edges`로 관리합니다.
- `round`와 `max_rounds`는 `AgentState`에서 관리합니다.
- MVP 기본값은 `max_rounds=2`입니다.
- 같은 라운드 안에서는 Debater 발언 순서를 고정해도 됩니다.
- Judge 노드는 반드시 마지막에 한 번만 실행합니다.
- 안전 이슈 또는 입력 부족 상태에서는 Debater 노드를 실행하지 않습니다.

## 7. API 규칙

### 7-1. 엔드포인트

필수 엔드포인트:

```text
POST /api/v1/chat/sync
POST /api/v1/chat
GET  /health
```

### 7-2. `/chat/sync`

동기 방식으로 전체 결과를 반환합니다.

요청:

```json
{
  "message": "중견기업 합격과 대기업 최종 면접 중 어디를 선택해야 할까?",
  "thread_id": "optional-thread-id"
}
```

응답 목표:

```json
{
  "debate_log": [
    {
      "round": 1,
      "agent": "realist",
      "stance": "중견기업 합격을 우선 보존해야 한다.",
      "content": "..."
    }
  ],
  "final_decision": {
    "recommendation": "...",
    "reasons": ["...", "...", "..."],
    "risks": ["..."]
  }
}
```

### 7-3. `/chat` SSE

SSE 이벤트는 프론트엔드가 순차 렌더링할 수 있게 아래 이벤트명을 사용합니다.

| event | 의미 |
|---|---|
| `moderator` | 토론 주제 정리 또는 입력 보완 질문 |
| `debater` | 각 Debater의 라운드별 발언 |
| `judge` | 최종 결론 |
| `error` | 예외 또는 일부 Agent 실패 |
| `done` | 스트림 종료 |

## 8. Prompt 작성 규칙

### 8-1. 공통 가드레일

모든 Agent prompt에는 다음 원칙을 포함합니다.

- 사용자가 제공하지 않은 사실을 단정하지 않는다.
- 의학·법률·금융 투자 등 전문 자격이 필요한 판단은 단정하지 않는다.
- 자해·자살·폭력 위험이 있으면 토론하지 않고 안전 안내로 전환한다.
- 결론을 회피하지 않는다. 단, 정보 부족 시 필요한 정보를 질문한다.
- 사용자에게 외부 행동을 대신 수행했다고 말하지 않는다.

### 8-2. Debater 출력 형식

Debater는 짧고 명확하게 말합니다.

```text
[주장]
...

[근거]
...

[반박/보강]
...
```

권장 길이:

- 라운드당 150~250자
- 한 발언에서 논점 1~2개만 다룸

### 8-3. Judge 출력 형식

Judge는 반드시 구조화된 형태로 출력합니다.

```json
{
  "recommendation": "실행 가능한 단일 추천",
  "reasons": ["이유 1", "이유 2", "이유 3"],
  "risks": ["리스크 1", "리스크 2"],
  "next_action": "사용자가 바로 할 수 있는 다음 행동"
}
```

## 9. Frontend 구현 규칙

Streamlit UI는 데모 안정성을 우선합니다.

필수 UI 요소:

- 고민 입력창
- 토론 시작 버튼 또는 `st.chat_input`
- Agent별 메시지 구분
  - 현실주의자
  - 이상주의자
  - 리스크 회피형
  - 사회자
  - 결론 Agent
- 로딩 상태 표시
- 최종 결론 카드
- 에러 메시지

UI 원칙:

- 토론 과정이 “관전”되는 느낌을 줍니다.
- 결론 카드는 토론 메시지보다 더 눈에 띄게 배치합니다.
- API 오류는 스택트레이스 그대로 보여주지 말고 사용자 친화 문구로 감쌉니다.

## 10. 테스트 및 완료 기준

작업 완료 전 최소 확인:

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
uv run streamlit run frontend/ui.py --server.port=8002
```

API 확인:

```bash
curl -X POST "http://localhost:8001/api/v1/chat/sync" \
  -H "Content-Type: application/json" \
  -d '{"message":"휴학하고 인턴을 할지, 졸업까지 마칠지 고민이야."}'
```

완료 기준:

- 단일 Python 또는 API 호출로 고민 입력 → 2라운드 토론 → 결론 JSON이 동작합니다.
- Streamlit에서 고민 입력 → 토론 관전 → 결론 카드 확인이 가능합니다.
- 입력 부족, 민감 주제, API 실패에 대한 최소 예외 처리가 있습니다.
- Docker Compose 또는 `start.sh`로 로컬 실행이 가능합니다.

## 11. 협업 규칙

### 11-1. 브랜치

- `main`: 제출 가능한 안정 버전
- `feat/...`: 기능 개발
- `fix/...`: 버그 수정
- `docs/...`: 문서 수정
- `refactor/...`: 구조 개선

### 11-2. 커밋 메시지

형식:

```text
<type>(<scope>): <변경 의도>
```

예시:

```text
feat(agent): 현실주의자 Debater system prompt 구현
feat(graph): 2라운드 토론 루프 조건 추가
fix(api): SSE done 이벤트 누락 수정
refactor(prompt): Debater 공통 가드레일 분리
docs(readme): 협업 규칙과 실행 방법 추가
```

### 11-3. PR

PR 본문에는 반드시 아래 항목을 포함합니다.

```markdown
## 무엇을 변경했는가

## 왜 변경했는가

## 어떻게 확인할 수 있는가

## 아직 남아 있는 이슈
```

PR 규칙:

- `main` 직접 push 금지
- 최소 1명 리뷰 후 merge
- 막힌 작업은 Draft PR로 공유
- PR 제목과 본문만 봐도 작업 맥락을 알 수 있게 작성

## 12. 코치/리뷰어에게 질문하는 방식

질문에는 반드시 다음 3가지를 포함합니다.

1. 목적: 왜 이 작업을 하는가
2. 시도: 어떤 방법을 해봤는가
3. 문제: 무엇이 기대와 다르게 동작하는가

좋은 질문 예시:

```text
사용자 고민을 3개 Debater로 순차 라우팅하는 그래프를 만들기 위해
StateGraph에서 realist → idealist → risk_averse → round_check 구조를 구현했습니다.
하지만 max_rounds=2일 때 Judge로 넘어가기 전에 round가 한 번 더 증가합니다.
현재 graph.py의 조건부 엣지와 AgentState 업데이트 방식이 적절한지 확인 부탁드립니다.
PR: <링크>
```

## 13. 금지 사항

- `main`에 직접 push하지 않습니다.
- 사용자가 제공하지 않은 개인정보나 상황을 추론해 결론의 근거로 쓰지 않습니다.
- 의료·법률·금융 투자 판단을 강하게 단정하지 않습니다.
- MVP 제외 기능을 구현하느라 필수 토론 흐름을 지연시키지 않습니다.
- 프론트엔드에 내부 예외 전체를 그대로 노출하지 않습니다.

## 14. 작업 우선순위

1. `schemas.py`에 DebateGraph 상태와 응답 스키마 정의
2. Debater/Moderator/Judge prompt 작성
3. Agent 노드 함수 구현
4. `graph.py`에 DebateGraph 구현
5. `/chat/sync` 응답 구조 정리
6. `/chat` SSE 스트림 구현
7. Streamlit UI에서 Agent별 토론 로그와 결론 카드 렌더링
8. 예외 처리 및 데모 시나리오 검증
9. README 최신화
