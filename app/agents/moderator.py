import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.safety import has_safety_risk
from app.core.llm import get_llm
from app.prompts import MODERATOR_SYSTEM_PROMPT
from app.schemas import AgentState, NormalizedProblem

logger = logging.getLogger(__name__)


class ModeratorOutput(BaseModel):
    normalized_problem: NormalizedProblem
    needs_clarification: bool
    clarification_questions: list[str] = Field(default_factory=list, max_length=2)
    safety_status: str = "safe"


def _fallback_moderation(query: str) -> ModeratorOutput:
    stripped = query.strip()

    if has_safety_risk(stripped):
        return ModeratorOutput(
            normalized_problem=NormalizedProblem(summary=stripped),
            needs_clarification=False,
            clarification_questions=[],
            safety_status="unsafe",
        )

    if len(stripped) < 12:
        return ModeratorOutput(
            normalized_problem=NormalizedProblem(summary=stripped),
            needs_clarification=True,
            clarification_questions=["어떤 선택지 사이에서 고민하고 있는지 알려줄 수 있나요?"],
            safety_status="safe",
        )

    return ModeratorOutput(
        normalized_problem=NormalizedProblem(
            summary=stripped,
            background=[stripped],
        ),
        needs_clarification=True,
        clarification_questions=[
            "지금 고려 중인 선택지들을 각각 알려줄 수 있나요?",
            "결정할 때 가장 중요하게 보는 기준은 무엇인가요?",
        ],
        safety_status="safe",
    )


def moderate_problem(state: AgentState) -> dict:
    """Normalize the user's concern and decide whether debate can start."""
    query = state["query"]
    logger.info("Agent started node=moderator query_chars=%s", len(query))

    if has_safety_risk(query):
        output = _fallback_moderation(query)
    else:
        try:
            llm = get_llm(temperature=0.0)
            structured_llm = llm.with_structured_output(ModeratorOutput)
            output = structured_llm.invoke(
                [
                    SystemMessage(content=MODERATOR_SYSTEM_PROMPT),
                    HumanMessage(content=query),
                ]
            )
        except Exception as exc:
            logger.warning("Moderator structured output failed: %s", exc)
            output = _fallback_moderation(query)

    data = output.model_dump()
    logger.info(
        "Agent completed node=moderator safety_status=%s needs_clarification=%s questions=%s options=%s criteria=%s",
        data["safety_status"],
        data["needs_clarification"],
        len(data["clarification_questions"]),
        len(data["normalized_problem"].get("options", [])),
        len(data["normalized_problem"].get("criteria", [])),
    )
    if data["needs_clarification"]:
        logger.info(
            "Debate paused by moderator summary_chars=%s questions=%s",
            len(data["normalized_problem"].get("summary", "")),
            len(data["clarification_questions"]),
        )
    return {
        "normalized_problem": data["normalized_problem"],
        "needs_clarification": data["needs_clarification"],
        "clarification_questions": data["clarification_questions"][:2],
        "safety_status": data["safety_status"],
    }
