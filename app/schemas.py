import operator
from uuid import uuid4
from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, field_validator
from typing_extensions import NotRequired, Required, TypedDict


DebateAgent = Literal["realist", "idealist", "risk_averse", "moderator"]
SafetyStatus = Literal["safe", "restricted", "unsafe"]


class NormalizedProblem(BaseModel):
    summary: str = ""
    options: list[str] = Field(default_factory=list)
    background: list[str] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)


class DebateTurn(BaseModel):
    round: int
    agent: DebateAgent
    stance: str
    content: str
    target: str | None = None


class FinalDecision(BaseModel):
    recommendation: str
    reasons: list[str] = Field(min_length=3, max_length=3)
    risks: list[str] = Field(min_length=1)
    next_action: str | None = None

    @field_validator("recommendation")
    @classmethod
    def recommendation_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("recommendation must not be blank")
        return value


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], operator.add]
    query: Required[str]

    # DebateGraph MVP state
    normalized_problem: Required[dict]
    debate_log: Required[list[dict]]
    round: Required[int]
    max_rounds: Required[int]
    final_decision: Required[dict]
    safety_status: Required[str]
    needs_clarification: Required[bool]
    clarification_questions: Required[list[str]]

    # Transitional fields used by the current medical QA graph.
    query_analysis: NotRequired[dict]
    search_results: NotRequired[list[dict]]
    final_answer: NotRequired[str]
    domain: NotRequired[str]
    iteration_count: NotRequired[int]


class QueryAnalysis(BaseModel):
    keywords: list[str] = Field(description="keywords")
    domain: Literal["medical", "general", "out_of_scope"] = Field(description="domain")
    intent: str = Field(description="intent")
    status: Literal["success", "insufficient"] = Field(description="status")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: str | None = Field(default_factory=lambda: str(uuid4()))


class ChatResponse(BaseModel):
    thread_id: str | None = None
    normalized_problem: NormalizedProblem = Field(default_factory=NormalizedProblem)
    debate_log: list[DebateTurn] = Field(default_factory=list)
    final_decision: FinalDecision | None = None
    needs_clarification: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    safety_status: SafetyStatus = "safe"


class StreamEvent(BaseModel):
    event: str = "message"
    node: str = ""
    data: str = ""
