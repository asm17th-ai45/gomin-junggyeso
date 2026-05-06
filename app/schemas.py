import operator
from uuid import uuid4
from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from typing_extensions import NotRequired, Required, TypedDict


class DebateTurn(BaseModel):
    round: int
    agent: Literal["realist", "idealist", "risk_averse", "moderator"]
    stance: str
    content: str
    target: str | None = None


class FinalDecision(BaseModel):
    recommendation: str
    reasons: list[str] = Field(min_length=3, max_length=3)
    risks: list[str] = Field(min_length=1)
    next_action: str | None = None


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
    thread_id: str = Field(default_factory=lambda: str(uuid4()))


class ChatResponse(BaseModel):
    answer: str
    domain: str = ""
    sources: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class StreamEvent(BaseModel):
    event: str = "message"
    node: str = ""
    data: str = ""
