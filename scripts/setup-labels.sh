#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI(gh)가 필요합니다. 먼저 gh를 설치하고 로그인하세요."
  exit 1
fi

labels=(
  "role:pm|7057ff|PM 담당 이슈"
  "role:agent-lead|1d76db|AI/Agent Lead 담당 이슈"
  "role:agent-sub|54aeef|AI/Agent Sub 담당 이슈"
  "role:backend|0e8a16|Backend 담당 이슈"
  "role:frontend|fbca04|Frontend 담당 이슈"

  "type:docs|0075ca|문서 작업"
  "type:feat|0e8a16|기능 구현"
  "type:fix|d73a4a|버그 수정"
  "type:chore|cfd3d7|설정, 인프라, 기타 작업"

  "area:agent|5319e7|Agent 로직 영역"
  "area:prompt|a2eeef|Prompt 영역"
  "area:graph|1d76db|LangGraph 흐름 영역"
  "area:api|0052cc|API 영역"
  "area:frontend|fbca04|Frontend 영역"
  "area:infra|cfd3d7|Infra 영역"
  "area:docs|0075ca|Docs 영역"

  "priority:p0|b60205|MVP 동작을 막는 핵심 필수 작업"
  "priority:p1|d93f0b|MVP 데모 품질과 안정성에 필요한 주요 작업"
  "priority:p2|fbca04|구현 후 정리/문서화/후속 보강 작업"
)

existing_labels="$(gh label list --limit 500 --json name --jq '.[].name')"

for item in "${labels[@]}"; do
  IFS="|" read -r name color description <<< "$item"

  if grep -Fxq "$name" <<< "$existing_labels"; then
    gh label edit "$name" --color "$color" --description "$description"
    echo "updated: $name"
  else
    gh label create "$name" --color "$color" --description "$description"
    echo "created: $name"
  fi
done
