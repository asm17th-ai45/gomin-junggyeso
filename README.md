# 고민중계소

> 내 고민을 던지면, 성격이 다른 AI들이 대신 토론해서 결론까지 내려주는 멀티 에이전트 의사결정 지원 서비스

## 1. 프로젝트 소개

**고민중계소**는 사용자의 진로·학업·커리어 고민에 대해 서로 다른 관점을 가진 AI Agent들이 토론하고, 최종적으로 근거 기반의 추천 결론을 제시하는 서비스입니다.

기존 단일 챗봇이 장단점을 균형 있게 정리하는 데 그쳤다면, 고민중계소는 현실주의자·이상주의자·리스크 회피형 Agent가 서로 다른 판단 기준으로 충돌하며 사용자가 자신의 우선순위를 발견하도록 돕습니다.

핵심 가치는 다음과 같습니다.

- 고민을 단순 정리가 아닌 **결정 가능한 형태**로 바꾼다.
- 결론뿐 아니라 **토론 과정**을 보여주어 사용자가 판단 근거를 확인할 수 있게 한다.
- 대학생·취준생처럼 진로와 커리어 선택 앞에서 판단 기준이 충돌하는 사용자를 우선 대상으로 한다.

## 2. 주요 기능

### MVP 포함 기능

- 자유 텍스트 기반 고민 입력
- 3개 Debater Agent 토론
  - 현실주의자 Agent: 실현 가능성, 현재 제약, 단기 비용/수익 중심
  - 이상주의자 Agent: 장기 가치, 성장, 의미, 만족도 중심
  - 리스크 회피형 Agent: 최악의 시나리오, 회복 가능성, 안정성 중심
- Moderator Agent의 토론 흐름 관리
- Judge/Synthesizer Agent의 최종 결론 생성
- 2라운드 토론 진행
- 결론 카드 출력
  - 최종 추천
  - 핵심 이유 3가지
  - 감수해야 할 리스크
- FastAPI 백엔드
- Streamlit 프론트엔드
- Docker Compose 또는 실행 스크립트 기반 로컬 실행

### MVP 제외 범위

- 사용자 계정/로그인
- 과거 고민 기록 저장 및 장기 메모리
- 외부 데이터 RAG 실제 적용
- 4번째 도전자 Agent
- 재토론/관점 추가 기능
- 모바일 전용 UI
- 음성 입력
- 결론 공유 기능

## 3. 사용자 흐름

1. 사용자가 고민과 배경 정보를 입력합니다.
2. Moderator Agent가 고민의 선택지, 배경 정보, 판단 기준을 정리합니다.
3. 현실주의자·이상주의자·리스크 회피형 Agent가 1라운드 입장을 제시합니다.
4. 각 Agent가 이전 발언을 참고해 2라운드 반박 또는 보강 발언을 합니다.
5. Moderator Agent가 토론 종료를 판단합니다.
6. Judge Agent가 토론 로그를 종합해 최종 결론 JSON을 생성합니다.
7. UI는 Agent별 발언과 최종 결론 카드를 사용자에게 보여줍니다.

## 4. 시스템 아키텍처

```text
[Streamlit UI]
     │  httpx / SSE
     ▼
[FastAPI API]
     │
     ▼
[LangGraph DebateGraph]
   START
     │
     ▼
[Moderator]
     │
     ▼
[Round Dispatcher]
     │
     ├─► [Realist Debater]
     ├─► [Idealist Debater]
     └─► [Risk-Averse Debater]
     │
     ▼
[Round Check]
     │  max_rounds 미도달 시 반복
     ▼
[Judge / Synthesizer]
     │
     ▼
   END
```

## 5. 기술 스택

| 영역 | 기술 |
|---|---|
| Language | Python 3.11+ |
| Package Manager | uv |
| LLM | Upstage Solar (`solar-pro2`) |
| Agent Orchestration | LangGraph, LangChain Core |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| Frontend | Streamlit, httpx |
| Optional Vector DB | ChromaDB |
| Environment | Docker Compose, `.env` |

## 6. 프로젝트 구조

고민중계소 MVP는 아래 구조를 기준으로 구현합니다. Agent, Graph, API, UI 책임을 분리하여 각 팀원이 담당 영역을 명확히 파악할 수 있게 합니다.

```text
.
├── app/
│   ├── agents/              # Agent 노드 함수
│   │   ├── debaters.py       # 현실주의자/이상주의자/리스크 회피형 Agent
│   │   ├── moderator.py      # 토론 주제 정리 및 라운드 관리
│   │   └── judge.py          # 최종 결론 생성
│   ├── core/                # LLM, 설정, 공통 인프라
│   ├── prompts/             # System prompt / prompt template
│   ├── api.py               # FastAPI 라우터
│   ├── graph.py             # LangGraph DebateGraph
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   └── schemas.py           # Pydantic / TypedDict 스키마
├── frontend/
│   └── ui.py                # Streamlit UI
├── data/                    # 확장용 데이터
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.frontend
├── pyproject.toml
├── start.sh
└── README.md
```

## 7. 환경 변수

`.env.example`을 복사해 `.env`를 생성합니다.

```bash
cp .env.example .env
```

필수 값:

```env
UPSTAGE_API_KEY=your_upstage_api_key
BACKEND_URL=http://127.0.0.1:8001
CORS_ORIGINS=http://127.0.0.1:8002
```

선택 값:

```env
CHROMA_MODE=embedded
CHROMA_HOST=localhost
CHROMA_PORT=8000
LANGSMITH_API_KEY=
LANGSMITH_TRACING=false
```

## 8. 로컬 실행 방법

### 8-1. uv로 실행

```bash
uv sync
bash start.sh
```

실행 후 접속 주소:

- Backend: <http://localhost:8001>
- Frontend: <http://localhost:8002>
- Health Check: <http://localhost:8001/health>

### 8-2. Docker Compose로 실행

```bash
docker compose up --build
```

### 8-3. API 테스트

```bash
curl -X POST "http://localhost:8001/api/v1/chat/sync" \
  -H "Content-Type: application/json" \
  -d '{"message":"중견기업 합격과 대기업 최종 면접 중 어떤 선택을 해야 할지 고민이야."}'
```

응답 목표 형식:

```json
{
  "final_decision": {
    "recommendation": "대기업 면접 결과를 기다리되, 중견기업에 일정 연장 요청을 시도한다.",
    "reasons": [
      "확정된 선택지를 보존하면서 더 큰 기회를 확인할 수 있다.",
      "일정 연장 요청은 리스크 대비 비용이 낮다.",
      "사용자의 성장성과 안정성 기준을 동시에 반영한다."
    ],
    "risks": [
      "중견기업이 일정 연장을 거절할 수 있다.",
      "대기업 면접 결과가 늦어질 수 있다."
    ]
  }
}
```

## 9. 개발 마일스톤

| 단계 | 기간 | 목표 | 완료 기준 |
|---|---:|---|---|
| 기획 | 4/27 ~ 5/2 | 문제 정의, Agent 역할, 기술 스택 확정 | 팀원 모두가 서비스와 토론 흐름을 동일하게 설명 가능 |
| Agent Workflow | 5/3 ~ 5/6 | LangGraph 멀티 에이전트 토론 그래프 구현 | 고민 입력 → 2라운드 토론 → 결론 JSON 동작 |
| Backend | 5/3 ~ 5/7 | `/chat/sync`, `/chat` SSE 구현 | curl 요청으로 결론 JSON 반환, SSE 이벤트 순차 전송 |
| Frontend | 5/6 ~ 5/8 | Streamlit UI 구현 | 고민 입력 → 토론 관전 → 결론 카드 확인 가능 |
| 통합/개선 | 5/9 | E2E 안정화 및 가드레일 점검 | 핵심 시나리오 2종이 끊김 없이 동작 |
| 최종 제출 | ~5/10 | 데모 영상 및 코드 제출 | 입력 → 토론 → 결론 전체 흐름 녹화 완료 |
| 발표 준비 | 5/11 ~ 5/17 | 발표 슬라이드 및 리허설 | 시연 1회 이상 리허설 완료 |

## 10. 팀 역할

| 역할 | 책임 |
|---|---|
| PM | 일정 관리, 방향 정리, 코치 커뮤니케이션, 기획서 총괄 |
| AI/Agent Lead | LangGraph 그래프 설계, AgentState 정의, Moderator/Judge 노드, 라운드 루프 구현 |
| AI/Agent Sub | Debater System Prompt 작성·튜닝, Pydantic 출력 스키마, 가드레일 처리 |
| Backend | FastAPI 엔드포인트, SSE 스트리밍, 예외/타임아웃 처리, Docker 패키징 |
| Frontend | Streamlit UI, Agent별 메시지 렌더링, 결론 카드, 백엔드 연동 |

## 11. 협업 규칙

### 11-1. 기본 원칙

- `main` 브랜치에 직접 push 하지 않습니다.
- 모든 작업은 Issue 단위로 관리합니다.
- 한 Issue는 1~2일 내 끝낼 수 있는 크기로 쪼갭니다.
- 막히면 혼자 오래 끌지 않고 30분~1시간 내 공유합니다.
- 모든 PR은 최소 1명 리뷰 후 merge합니다.
- 리뷰는 24시간 내 1차 응답을 원칙으로 합니다.

### 11-2. 브랜치 규칙

| 브랜치 | 용도 | 예시 |
|---|---|---|
| `main` | 제출 가능한 안정 버전 | - |
| `feat/...` | 기능 개발 | `feat/agent-debater-realist`, `feat/api-chat-sse` |
| `fix/...` | 버그 수정 | `fix/judge-empty-output` |
| `docs/...` | 문서 수정 | `docs/update-readme` |
| `refactor/...` | 구조 개선 | `refactor/agent-state-schema` |

### 11-3. 커밋 규칙

커밋 메시지는 다음 형식을 사용합니다.

```text
<type>(<scope>): <변경 의도>
```

사용 가능한 type:

- `feat`: 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `refactor`: 구조 개선
- `test`: 테스트 추가/수정
- `chore`: 환경 설정, 빌드, 기타 작업

권장 scope:

- `agent`
- `api`
- `frontend`
- `graph`
- `prompt`
- `infra`

예시:

```text
feat(agent): 현실주의자 Debater system prompt 1차 구현
feat(graph): 라운드 종료 조건을 위한 conditional edge 추가
fix(api): SSE 스트림에서 마지막 이벤트 누락 수정
docs(readme): 로컬 실행 방법과 협업 규칙 추가
refactor(prompt): Debater 공통 가드레일을 template로 분리
chore(infra): docker-compose에 .env 마운트 추가
```

### 11-4. PR 템플릿

```markdown
## 무엇을 변경했는가

## 왜 변경했는가

## 어떻게 확인할 수 있는가

## 아직 남아 있는 이슈
```

### 11-5. 커뮤니케이션 규칙

- 작업 시작 전: 오늘 할 일을 짧게 공유합니다.
- 작업 중 막힘: 현재 상태, 시도한 방법, 필요한 도움을 포함해 공유합니다.
- 작업 완료 후: PR 링크 또는 실행 결과를 공유합니다.
- 주요 의사결정: Notion 또는 회의록에 날짜, 결정 내용, 이유를 남깁니다.

## 12. 가드레일

- 의료·법률·금융 투자처럼 전문 자격이 필요한 판단은 단정적 결론을 피하고 전문가 상담을 권합니다.
- 자해, 자살, 폭력 의도가 감지되면 토론을 시작하지 않고 안전 안내 메시지로 응답합니다.
- 사용자가 제공하지 않은 개인정보를 추론해 판단 근거로 삼지 않습니다.
- 입력 정보가 부족하면 토론을 시작하기 전 핵심 질문 1~2개를 되묻습니다.
- LLM API 실패 또는 타임아웃이 발생하면 일부 Agent 응답 누락을 사용자에게 알리고 가능한 범위에서 진행합니다.

## 13. 데모 시나리오

### 시나리오 1: 취업 선택

```text
중견기업에는 최종 합격했고, 대기업은 최종 면접을 앞두고 있어.
중견기업은 안정적이지만 성장 가능성이 조금 아쉽고,
대기업은 붙으면 좋지만 떨어질 가능성도 있어.
어떤 선택을 해야 할까?
```

### 시나리오 2: 휴학 vs 학업 지속

```text
대학교 3학년인데 이번 학기에 휴학하고 인턴을 할지,
그냥 졸업까지 마칠지 고민이야.
인턴은 개발 직무와 관련 있지만 아직 확정된 건 아니야.
```

## 14. 라이선스

프로젝트 제출용 팀 레포지토리입니다. 별도 라이선스를 정하기 전까지 외부 배포를 제한합니다.
