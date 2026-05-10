import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.prompts import JUDGE_SYSTEM_PROMPT
from app.schemas import AgentState, FinalDecision

logger = logging.getLogger(__name__)


def _build_judge_input(state: AgentState) -> str:
    payload = {
        "normalized_problem": state.get("normalized_problem", {}),
        "debate_log": state.get("debate_log", []),
        "safety_status": state.get("safety_status", "safe"),
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def _fallback_decision(state: AgentState) -> FinalDecision:
    safety_status = state.get("safety_status", "safe")
    normalized_problem = state.get("normalized_problem", {})
    summary = normalized_problem.get("summary") or state.get("query", "현재 고민")
    options = normalized_problem.get("options", [])

    if safety_status == "unsafe":
        return FinalDecision(
            recommendation="지금은 선택을 결론내리기보다 즉시 안전을 확보하는 것을 우선하세요.",
            reasons=[
                "자해나 폭력 위험이 감지되면 토론보다 안전 확보가 먼저입니다.",
                "위험이 높은 상태에서는 장기 선택을 차분히 비교하기 어렵습니다.",
                "신뢰할 수 있는 사람이나 긴급 지원에 연결되는 것이 회복 가능성을 높입니다.",
            ],
            risks=["혼자 판단을 이어가면 위험 신호가 커질 수 있습니다."],
            next_action="지금 곁에 있는 사람에게 연락하거나 지역 긴급 지원 창구에 도움을 요청하세요.",
        )

    if options:
        recommendation = f"{options[0]} 쪽을 우선 검토하세요."
    else:
        recommendation = f"{summary}에 대해 선택지를 먼저 좁힌 뒤 결정하세요."

    return FinalDecision(
        recommendation=recommendation,
        reasons=[
            "현재 제공된 정보 안에서 가장 실행 가능한 방향을 먼저 정리해야 합니다.",
            "판단 기준을 명확히 하면 현실성, 성장 가능성, 안정성을 비교하기 쉽습니다.",
            "선택지를 좁힌 뒤 리스크를 확인해야 다음 행동으로 옮길 수 있습니다.",
        ],
        risks=["제공된 정보가 부족하면 추천 방향이 달라질 수 있습니다."],
        next_action="결정에 필요한 핵심 조건 1가지를 적어보고 선택지별로 비교하세요.",
    )


def synthesize_decision(state: AgentState) -> dict:
    """Synthesize debate turns into a structured final decision."""
    logger.info(
        "Agent started node=judge safety_status=%s debate_turns=%s",
        state.get("safety_status", "safe"),
        len(state.get("debate_log", [])),
    )
    if state.get("safety_status") == "unsafe":
        decision = _fallback_decision(state)
    else:
        try:
            llm = get_llm(temperature=0.0)
            structured_llm = llm.with_structured_output(FinalDecision)
            decision = structured_llm.invoke(
                [
                    SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                    HumanMessage(content=_build_judge_input(state)),
                ]
            )
        except Exception as exc:
            logger.warning("Judge structured output failed: %s", exc)
            decision = _fallback_decision(state)

    logger.info(
        "Agent completed node=judge recommendation_chars=%s reasons=%s risks=%s",
        len(decision.recommendation),
        len(decision.reasons),
        len(decision.risks),
    )
    return {"final_decision": decision.model_dump()}
