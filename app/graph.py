import logging

from langgraph.graph import END, START, StateGraph

from app.agents import idealist, moderate_problem, realist, risk_averse, safety_check, synthesize_decision
from app.schemas import AgentState

logger = logging.getLogger(__name__)


def route_after_safety(state: AgentState) -> str:
    return "judge" if state.get("safety_status") == "unsafe" else "moderator"


def route_after_moderator(state: AgentState) -> str:
    if state.get("safety_status") != "safe" or state.get("needs_clarification"):
        return "end"
    return "realist"


def round_check(state: AgentState) -> dict:
    current_round = state.get("round", 1)
    next_round = current_round + 1
    logger.info(
        "Agent completed node=round_check current_round=%s next_round=%s max_rounds=%s",
        current_round,
        next_round,
        state.get("max_rounds", 2),
    )
    return {"round": next_round}


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
