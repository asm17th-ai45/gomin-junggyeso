from app.schemas import AgentState

SAFETY_KEYWORDS = (
    "자살",
    "죽고 싶",
    "죽을래",
    "자해",
    "해치고 싶",
    "죽이고 싶",
    "폭력",
)


def has_safety_risk(query: str) -> bool:
    return any(keyword in query for keyword in SAFETY_KEYWORDS)


def safety_check(state: AgentState) -> dict:
    safety_status = "unsafe" if has_safety_risk(state["query"]) else "safe"
    return {"safety_status": safety_status}
