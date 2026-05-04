import operator
from uuid import uuid4
from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

class DebateTurn(BaseModel):
    round: int
    agent: Literal["realist", "idealist", "risk_averse", "moderator"]
    stance: str
    content: str
    target: str | None = None

class FinalDecision(BaseModel):
    recommendation: str
    reasons: list[str]
    risks: list[str]
    next_action: str | None = None

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    query: str
    normalized_problem: dict
    debate_log: list[dict]
    round: int
    max_rounds: int
    final_decision: dict
    safety_status: str
    needs_clarification: bool
    clarification_questions: list[str]

class QueryAnalysis(BaseModel):
    keywords: list[str] = Field(description="keywords")
    domain: Literal["medical","general","out_of_scope"] = Field(description="domain")
    intent: str = Field(description="intent")
    status: Literal["success","insufficient"] = Field(description="status")

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
