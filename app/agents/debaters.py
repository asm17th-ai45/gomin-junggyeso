import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.core.llm import get_llm
from app.prompts import IDEALIST_SYSTEM_PROMPT, REALIST_SYSTEM_PROMPT, RISK_AVERSE_SYSTEM_PROMPT
from app.schemas import AgentState, DebateTurn

logger = logging.getLogger(__name__)


class DebaterOutput(BaseModel):
    stance: str
    content: str


_FALLBACKS: dict[str, dict] = {
    "realist": {
        "stance": "현재 조건에서 실행 가능성이 가장 높은 선택을 우선해야 한다.",
        "content": (
            "[주장]\n지금 확정된 선택지 중 바로 실행 가능한 방향을 먼저 좁혀야 합니다.\n\n"
            "[근거]\n시간, 비용, 확정된 제약을 기준으로 판단해야 후속 손실을 줄일 수 있습니다.\n\n"
            "[반박/보강]\n장기 만족도도 중요하지만, 현재 감당 가능한 범위를 넘기면 결정 지속성이 낮아집니다."
        ),
    },
    "idealist": {
        "stance": "장기 가치와 성장 가능성을 함께 고려해야 한다.",
        "content": (
            "[주장]\n단기 안정만으로 결론내리기보다 선택 이후에 남을 가치를 먼저 봐야 합니다.\n\n"
            "[근거]\n성장, 의미, 만족도는 선택 이후의 지속 동기를 만듭니다.\n\n"
            "[반박/보강]\n현실 제약을 무시하자는 뜻이 아니라, 감당 가능한 범위 안에서 더 큰 가능성을 선택해야 합니다."
        ),
    },
    "risk_averse": {
        "stance": "실패했을 때 회복 가능한 선택인지 먼저 확인해야 한다.",
        "content": (
            "[주장]\n최악의 경우에도 회복 가능한지를 먼저 따져야 합니다.\n\n"
            "[근거]\n손실 규모와 되돌릴 수 있는지를 확인해야 후회 비용을 줄일 수 있습니다.\n\n"
            "[반박/보강]\n위험을 피하기만 하자는 뜻이 아니라, 위험을 줄이는 조건을 붙이면 선택지가 더 선명해집니다."
        ),
    },
}


def _build_debater_input(state: AgentState) -> str:
    payload = {
        "normalized_problem": state.get("normalized_problem", {}),
        "debate_log": state.get("debate_log", []),
        "round": state.get("round", 1),
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def _run_debater(state: AgentState, agent: str, system_prompt: str) -> dict:
    try:
        llm = get_llm(temperature=0.7)
        structured_llm = llm.with_structured_output(DebaterOutput)
        output: DebaterOutput = structured_llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=_build_debater_input(state)),
            ]
        )
    except Exception as exc:
        logger.warning("%s structured output failed: %s", agent, exc)
        output = DebaterOutput(**_FALLBACKS[agent])

    turn = DebateTurn(
        round=state.get("round", 1),
        agent=agent,
        stance=output.stance,
        content=output.content,
    )
    return {"debate_log": [*state.get("debate_log", []), turn.model_dump()]}


def realist(state: AgentState) -> dict:
    return _run_debater(state, "realist", REALIST_SYSTEM_PROMPT)


def idealist(state: AgentState) -> dict:
    return _run_debater(state, "idealist", IDEALIST_SYSTEM_PROMPT)


def risk_averse(state: AgentState) -> dict:
    return _run_debater(state, "risk_averse", RISK_AVERSE_SYSTEM_PROMPT)
