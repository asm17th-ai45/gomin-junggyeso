#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI(gh)가 필요합니다. 먼저 gh를 설치하고 로그인하세요."
  exit 1
fi

existing_issues="$(gh issue list --state all --limit 500 --json title --jq '.[].title')"

create_issue() {
  local title="$1"
  local labels="$2"
  local body="$3"

  if grep -Fxq "$title" <<< "$existing_issues"; then
    echo "skipped: $title"
    return
  fi

  gh issue create \
    --title "$title" \
    --label "$labels" \
    --body "$body"

  echo "created: $title"
}

create_issue "docs: README와 AGENTS.md 초기 세팅" \
  "role:pm,type:docs,area:docs,priority:p0" \
  "README.md와 AGENTS.md에 프로젝트 목표, MVP 범위, 협업 규칙을 정리한다.

AC:
- README에 프로젝트 소개, 실행 방법, 마일스톤이 포함된다.
- AGENTS.md에 Agent 구현 규칙과 완료 기준이 포함된다."

create_issue "docs(readme): 실행 방법과 데모 시나리오 최신화" \
  "role:pm,type:docs,area:docs,priority:p2" \
  "구현 결과에 맞춰 README 실행 방법과 데모 시나리오를 최신화한다.

AC:
- uv, Docker Compose 실행 방법이 실제 동작과 일치한다.
- API와 Streamlit 데모 확인 방법이 포함된다."

create_issue "feat(agent): AgentState 스키마 정의" \
  "role:agent-lead,type:feat,area:agent,priority:p0" \
  "DebateGraph 상태 흐름에 필요한 AgentState TypedDict를 정의한다.

AC:
- query, normalized_problem, debate_log, round, max_rounds, final_decision, safety_status, needs_clarification, clarification_questions를 포함한다.
- LangGraph 노드 간 상태 전달에 사용할 수 있다."

create_issue "feat(prompt): Moderator/Judge system prompt 작성" \
  "role:agent-lead,type:feat,area:prompt,priority:p0" \
  "Moderator와 Judge/Synthesizer의 system prompt를 작성한다.

AC:
- Moderator는 선택지, 배경 정보, 판단 기준을 추출한다.
- 입력 부족 시 핵심 질문 1~2개를 반환한다.
- Judge는 recommendation, reasons, risks, next_action 구조로 결론을 반환한다."

create_issue "feat(agent): Moderator 노드 함수 구현" \
  "role:agent-lead,type:feat,area:agent,priority:p0" \
  "사용자 고민을 정리하고 토론 시작 가능 여부를 판단하는 Moderator 노드를 구현한다.

AC:
- normalized_problem을 채운다.
- 입력 부족 시 needs_clarification과 clarification_questions를 설정한다.
- 입력 부족 상태에서는 Debater가 실행되지 않도록 상태를 반환한다."

create_issue "feat(agent): Judge 노드 함수 구현" \
  "role:agent-lead,type:feat,area:agent,priority:p0" \
  "토론 로그를 종합해 구조화된 최종 결론을 만드는 Judge 노드를 구현한다.

AC:
- final_decision에 recommendation, reasons, risks를 포함한다.
- reasons는 3개를 목표로 한다.
- risks는 최소 1개 이상 포함한다."

create_issue "feat(graph): 2라운드 DebateGraph 구현" \
  "role:agent-lead,type:feat,area:graph,priority:p0" \
  "safety_check, moderator, debater 3종, round_check, judge를 연결하는 DebateGraph를 구현한다.

AC:
- 기본 max_rounds는 2다.
- Debater 순서는 realist, idealist, risk_averse로 고정한다.
- Judge는 마지막에 한 번만 실행된다.
- 안전 이슈 또는 입력 부족 상태에서는 Debater를 실행하지 않는다."

create_issue "feat(agent): Pydantic 출력 스키마 정의" \
  "role:agent-sub,type:feat,area:agent,priority:p0" \
  "프론트엔드 렌더링과 API 응답에 사용할 DebateTurn, FinalDecision 모델을 정의한다.

AC:
- DebateTurn은 round, agent, stance, content, target을 포함한다.
- FinalDecision은 recommendation, reasons, risks, next_action을 포함한다."

create_issue "feat(prompt): Debater 3종 system prompt 작성" \
  "role:agent-sub,type:feat,area:prompt,priority:p0" \
  "현실주의자, 이상주의자, 리스크 회피형 Debater system prompt를 작성한다.

AC:
- 각 Debater의 판단 기준과 말투가 분리된다.
- 사용자가 제공하지 않은 사실을 단정하지 않는다.
- Debater 출력은 주장, 근거, 반박/보강 형식을 따른다."

create_issue "feat(agent): safety_check 가드레일 노드 구현" \
  "role:agent-sub,type:feat,area:agent,priority:p0" \
  "민감 주제와 안전 위험을 감지하는 safety_check 노드를 구현한다.

AC:
- 자해, 자살, 폭력 위험이 감지되면 토론을 시작하지 않는다.
- 안전 안내 또는 안전 상태를 AgentState에 반영한다."

create_issue "feat(agent): Debater 3종 노드 함수 구현" \
  "role:agent-sub,type:feat,area:agent,priority:p0" \
  "Realist, Idealist, Risk-Averse Debater 노드 함수를 구현한다.

AC:
- 각 노드는 DebateTurn 형태로 debate_log에 발언을 추가한다.
- 라운드별 150~250자 수준의 짧고 명확한 발언을 생성한다.
- 이전 발언을 참고해 2라운드에서 반박 또는 보강한다."

create_issue "feat(api): Chat 요청/응답 스키마 정의" \
  "role:backend,type:feat,area:api,priority:p0" \
  "FastAPI 요청/응답에 사용할 Chat 스키마를 정의한다.

AC:
- 요청은 message와 optional thread_id를 받는다.
- 응답은 debate_log와 final_decision을 포함한다.
- 입력 부족 응답 구조를 프론트엔드가 처리할 수 있다."

create_issue "feat(api): /health 엔드포인트 구현" \
  "role:backend,type:feat,area:api,priority:p1" \
  "서비스 상태 확인용 /health 엔드포인트를 구현한다.

AC:
- GET /health가 200 응답을 반환한다.
- 로컬 실행 확인에 사용할 수 있는 간단한 상태 값을 반환한다."

create_issue "feat(api): /chat/sync 엔드포인트 구현" \
  "role:backend,type:feat,area:api,priority:p0" \
  "동기 방식으로 DebateGraph 전체 결과를 반환하는 /api/v1/chat/sync 엔드포인트를 구현한다.

AC:
- POST /api/v1/chat/sync가 message를 받아 DebateGraph를 실행한다.
- 응답에 debate_log와 final_decision이 포함된다.
- curl로 핵심 데모 시나리오를 확인할 수 있다."

create_issue "feat(api): /chat SSE 스트리밍 구현" \
  "role:backend,type:feat,area:api,priority:p1" \
  "프론트엔드 순차 렌더링을 위한 /api/v1/chat SSE 스트리밍 엔드포인트를 구현한다.

AC:
- moderator, debater, judge, error, done 이벤트를 전송한다.
- done 이벤트로 스트림 종료를 알린다."

create_issue "fix(api): 입력 부족/민감 주제/API 실패 응답 처리" \
  "role:backend,type:fix,area:api,priority:p1" \
  "입력 부족, 민감 주제, LLM/API 실패 상황의 최소 예외 처리를 구현한다.

AC:
- 스택트레이스를 사용자 응답에 노출하지 않는다.
- 입력 부족 시 보완 질문을 반환한다.
- 민감 주제는 토론 대신 안전 안내로 전환한다."

create_issue "chore(infra): 로컬 실행 스크립트 또는 Docker Compose 정리" \
  "role:backend,type:chore,area:infra,priority:p1" \
  "로컬 실행을 위한 start.sh 또는 Docker Compose 구성을 정리한다.

AC:
- uv 기반 실행 방법이 동작한다.
- Docker Compose 또는 start.sh로 백엔드와 프론트엔드를 실행할 수 있다."

create_issue "feat(frontend): 고민 입력 UI 구현" \
  "role:frontend,type:feat,area:frontend,priority:p0" \
  "Streamlit에서 사용자가 고민을 입력할 수 있는 UI를 구현한다.

AC:
- 고민 입력창 또는 st.chat_input이 제공된다.
- 토론 시작 버튼 또는 입력 제출 흐름이 명확하다."

create_issue "feat(frontend): Agent별 토론 메시지 렌더링" \
  "role:frontend,type:feat,area:frontend,priority:p0" \
  "Agent별 발언을 구분해 토론 관전 경험을 제공한다.

AC:
- 현실주의자, 이상주의자, 리스크 회피형, 사회자 메시지가 구분된다.
- debate_log를 순서대로 렌더링한다."

create_issue "feat(frontend): 최종 결론 카드 구현" \
  "role:frontend,type:feat,area:frontend,priority:p0" \
  "Judge의 최종 결론을 토론 메시지보다 눈에 띄는 카드로 렌더링한다.

AC:
- recommendation, reasons, risks, next_action을 표시한다.
- reasons 3개와 risks 목록을 읽기 쉽게 보여준다."

create_issue "feat(frontend): API 연동 및 로딩/에러 상태 처리" \
  "role:frontend,type:feat,area:frontend,priority:p0" \
  "Streamlit UI를 백엔드 API와 연결하고 로딩 및 에러 상태를 처리한다.

AC:
- /api/v1/chat/sync 또는 /api/v1/chat과 연동한다.
- 로딩 상태를 표시한다.
- API 오류를 사용자 친화 문구로 감싼다."
