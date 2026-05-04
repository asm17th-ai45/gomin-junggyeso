from langgraph.graph import END, START, StateGraph

from app.agents import moderate_problem, synthesize_decision
from app.schemas import AgentState, DebateTurn


SAFETY_KEYWORDS = (
    "자살",
    "죽고 싶",
    "죽을래",
    "자해",
    "해치고 싶",
    "죽이고 싶",
    "폭력",
)


def safety_check(state: AgentState) -> dict:
    query = state["query"]
    safety_status = "unsafe" if any(keyword in query for keyword in SAFETY_KEYWORDS) else "safe"

    return {
        "normalized_problem": state.get("normalized_problem", {}),
        "debate_log": state.get("debate_log", []),
        "round": state.get("round", 1),
        "max_rounds": state.get("max_rounds", 2),
        "final_decision": state.get("final_decision", {}),
        "safety_status": safety_status,
        "needs_clarification": state.get("needs_clarification", False),
        "clarification_questions": state.get("clarification_questions", []),
    }


def route_after_safety(state: AgentState) -> str:
    return "judge" if state.get("safety_status") == "unsafe" else "moderator"


def route_after_moderator(state: AgentState) -> str:
    if state.get("safety_status") != "safe" or state.get("needs_clarification"):
        return "end"
    return "realist"


def _problem_summary(state: AgentState) -> str:
    normalized_problem = state.get("normalized_problem", {})
    return normalized_problem.get("summary") or state["query"]


def _append_turn(state: AgentState, agent: str, stance: str, content: str) -> dict:
    turn = DebateTurn(
        round=state.get("round", 1),
        agent=agent,
        stance=stance,
        content=content,
    )
    return {"debate_log": [*state.get("debate_log", []), turn.model_dump()]}


def realist(state: AgentState) -> dict:
    summary = _problem_summary(state)
    return _append_turn(
        state,
        "realist",
        "현재 조건에서 실행 가능성이 가장 높은 선택을 우선해야 한다.",
        f"[주장]\n{summary}는 먼저 지금 당장 실행 가능한 선택지를 좁혀야 합니다.\n\n[근거]\n시간, 비용, 확정된 제약을 기준으로 판단해야 후속 손실을 줄일 수 있습니다.\n\n[반박/보강]\n장기 만족도도 중요하지만, 현재 감당 가능한 범위를 넘기면 결정 지속성이 낮아집니다.",
    )


def idealist(state: AgentState) -> dict:
    summary = _problem_summary(state)
    return _append_turn(
        state,
        "idealist",
        "장기 가치와 성장 가능성을 함께 고려해야 한다.",
        f"[주장]\n{summary}는 단기 안정만으로 결론내리기보다 장기적으로 남을 가치를 봐야 합니다.\n\n[근거]\n성장, 의미, 만족도는 선택 이후의 지속 동기를 만듭니다.\n\n[반박/보강]\n현실 제약을 무시하자는 뜻은 아니며, 감당 가능한 범위 안에서 더 큰 가능성을 선택해야 합니다.",
    )


def risk_averse(state: AgentState) -> dict:
    summary = _problem_summary(state)
    return _append_turn(
        state,
        "risk_averse",
        "실패했을 때 회복 가능한 선택인지 먼저 확인해야 한다.",
        f"[주장]\n{summary}는 최악의 경우에도 회복 가능한지 따져야 합니다.\n\n[근거]\n손실 규모와 되돌릴 수 있는지를 확인해야 후회 비용을 줄일 수 있습니다.\n\n[반박/보강]\n위험을 피하기만 하자는 뜻은 아니며, 위험을 줄이는 조건을 붙이면 선택지가 더 선명해집니다.",
    )


def round_check(state: AgentState) -> dict:
    return {"round": state.get("round", 1) + 1}


def route_after_round_check(state: AgentState) -> str:
    return "continue" if state.get("round", 1) <= state.get("max_rounds", 2) else "finish"


def create_graph():
    builder = StateGraph(AgentState)

    builder.add_node("safety_check", safety_check)
    builder.add_node("moderator", moderate_problem)
    builder.add_node("realist", realist)
    builder.add_node("idealist", idealist)
    builder.add_node("risk_averse", risk_averse)
    builder.add_node("round_check", round_check)
    builder.add_node("judge", synthesize_decision)

    builder.add_edge(START, "safety_check")
    builder.add_conditional_edges(
        "safety_check",
        route_after_safety,
        {"moderator": "moderator", "judge": "judge"},
    )
    builder.add_conditional_edges(
        "moderator",
        route_after_moderator,
        {"realist": "realist", "end": END},
    )
    builder.add_edge("realist", "idealist")
    builder.add_edge("idealist", "risk_averse")
    builder.add_edge("risk_averse", "round_check")
    builder.add_conditional_edges(
        "round_check",
        route_after_round_check,
        {"continue": "realist", "finish": "judge"},
    )
    builder.add_edge("judge", END)

    return builder.compile()
