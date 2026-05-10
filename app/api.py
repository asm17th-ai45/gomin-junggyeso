import asyncio
import json
import logging
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.schemas import ChatRequest, ChatResponse
from app.graph import create_graph

logger = logging.getLogger(__name__)
router = APIRouter()
graph = create_graph()
DEFAULT_MAX_ROUNDS = 2
DEFAULT_GRAPH_TIMEOUT_SECONDS = 90
STREAM_HEARTBEAT_SECONDS = 10
DEFAULT_CLARIFICATION_QUESTIONS = [
    "지금 고민 중인 선택지를 각각 알려줄 수 있나요?",
    "결정할 때 가장 중요하게 보는 기준은 무엇인가요?",
]
API_FAILURE_DECISION = {
    "recommendation": "일시적인 오류로 토론을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    "reasons": [
        "AI 토론 그래프 실행 중 문제가 발생했습니다.",
        "불완전한 토론 결과를 결론처럼 제공하지 않기 위해 안전 응답으로 전환했습니다.",
        "같은 요청을 다시 보내면 정상 응답을 받을 수 있습니다.",
    ],
    "risks": ["현재 응답에는 실제 Agent 토론 결과가 포함되어 있지 않습니다."],
    "next_action": "잠시 후 같은 고민으로 다시 토론을 시작해 주세요.",
}
RESTRICTED_DECISION = {
    "recommendation": "전문 자격이 필요한 사안은 단정적 결론 대신 정보를 정리하고 전문가와 상담하세요.",
    "reasons": [
        "의학, 법률, 금융 투자 판단은 개인 상황과 최신 기준에 따라 결과가 크게 달라질 수 있습니다.",
        "AI 토론만으로 확정적 결정을 내리면 중요한 위험을 놓칠 수 있습니다.",
        "현재 단계에서는 선택지를 정리하고 검증할 질문을 만드는 것이 더 안전합니다.",
    ],
    "risks": ["전문가 확인 없이 실행하면 건강, 법적 책임, 재정 손실이 발생할 수 있습니다."],
    "next_action": "현재 상황과 선택지를 정리한 뒤 관련 전문가에게 확인할 질문 3가지를 적어보세요.",
}


def build_initial_state(message: str, max_rounds: int = DEFAULT_MAX_ROUNDS) -> dict:
    """사용자 메시지로부터 그래프 초기 상태를 생성한다."""
    return {
        "messages": [HumanMessage(content=message)],
        "query": message,
        "normalized_problem": {},
        "debate_log": [],
        "round": 1,
        "max_rounds": max_rounds,
        "final_decision": {},
        "safety_status": "safe",
        "needs_clarification": False,
        "clarification_questions": [],
    }


def build_chat_response(thread_id: str | None, result: dict) -> ChatResponse:
    """DebateGraph 결과를 프론트엔드용 Chat 응답 스키마로 변환한다."""
    normalized_problem = result.get("normalized_problem") or {}
    if not normalized_problem.get("summary") and result.get("query"):
        normalized_problem = {**normalized_problem, "summary": result["query"]}

    needs_clarification = result.get("needs_clarification", False)
    clarification_questions = result.get("clarification_questions") or []
    if needs_clarification and not clarification_questions:
        clarification_questions = DEFAULT_CLARIFICATION_QUESTIONS

    safety_status = result.get("safety_status", "safe")
    final_decision = result.get("final_decision") or None
    if safety_status == "restricted" and final_decision is None:
        final_decision = RESTRICTED_DECISION

    return ChatResponse(
        thread_id=thread_id,
        normalized_problem=normalized_problem,
        debate_log=result.get("debate_log") or [],
        final_decision=final_decision,
        needs_clarification=needs_clarification,
        clarification_questions=clarification_questions,
        safety_status=safety_status,
    )


def build_api_failure_response(thread_id: str | None, message: str) -> ChatResponse:
    """그래프 실행 실패 시 스택트레이스 대신 같은 응답 스키마로 반환한다."""
    return build_chat_response(
        thread_id,
        {
            "query": message,
            "normalized_problem": {"summary": message},
            "debate_log": [],
            "final_decision": API_FAILURE_DECISION,
            "needs_clarification": False,
            "clarification_questions": [],
            "safety_status": "safe",
        },
    )


def format_sse(event: str, data: dict) -> str:
    """프론트엔드 EventSource/stream parser가 읽을 수 있는 SSE 문자열을 만든다."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def run_debate_graph(request: ChatRequest) -> tuple[ChatResponse, bool]:
    """DebateGraph를 실행하고 실패 여부와 함께 ChatResponse를 반환한다."""
    start = time.perf_counter()
    logger.info(
        "DebateGraph sync started thread_id=%s message_chars=%s",
        request.thread_id,
        len(request.message),
    )
    try:
        result = await asyncio.wait_for(
            graph.ainvoke(build_initial_state(request.message)),
            timeout=DEFAULT_GRAPH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("DebateGraph timed out for thread_id=%s", request.thread_id)
        return build_api_failure_response(request.thread_id, request.message), True
    except Exception as exc:
        logger.exception("DebateGraph failed for thread_id=%s: %s", request.thread_id, exc)
        return build_api_failure_response(request.thread_id, request.message), True

    response = build_chat_response(request.thread_id, result)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "DebateGraph sync completed thread_id=%s duration_ms=%.1f safety_status=%s clarification=%s turns=%s has_decision=%s",
        request.thread_id,
        duration_ms,
        response.safety_status,
        response.needs_clarification,
        len(response.debate_log),
        response.final_decision is not None,
    )
    return response, False


async def stream_debate_graph(request: ChatRequest):
    """DebateGraph 노드 완료 시점마다 SSE 이벤트를 순차 전송한다."""
    state = build_initial_state(request.message)
    queue = asyncio.Queue()
    start = time.perf_counter()
    logger.info(
        "DebateGraph stream started thread_id=%s message_chars=%s",
        request.thread_id,
        len(request.message),
    )

    async def produce_events():
        try:
            async for update in graph.astream(state, stream_mode="updates"):
                if "moderator" in update:
                    node_state = update["moderator"]
                    normalized_problem = node_state.get("normalized_problem") or {}
                    needs_clarification = node_state.get("needs_clarification", False)
                    clarification_questions = node_state.get("clarification_questions") or []
                    if needs_clarification and not clarification_questions:
                        clarification_questions = DEFAULT_CLARIFICATION_QUESTIONS

                    await queue.put(
                        format_sse(
                            "moderator",
                            {
                                "thread_id": request.thread_id,
                                "normalized_problem": normalized_problem,
                                "needs_clarification": needs_clarification,
                                "clarification_questions": clarification_questions,
                                "safety_status": node_state.get("safety_status", "safe"),
                            },
                        )
                    )
                    logger.info(
                        "SSE event queued event=moderator thread_id=%s clarification=%s questions=%s",
                        request.thread_id,
                        needs_clarification,
                        len(clarification_questions),
                    )

                for node_name in ("realist", "idealist", "risk_averse"):
                    if node_name in update:
                        debate_log = update[node_name].get("debate_log") or []
                        if debate_log:
                            payload = debate_log[-1]
                            payload["thread_id"] = request.thread_id
                            await queue.put(format_sse("debater", payload))
                            logger.info(
                                "SSE event queued event=debater thread_id=%s round=%s agent=%s content_chars=%s",
                                request.thread_id,
                                payload.get("round"),
                                payload.get("agent"),
                                len(payload.get("content", "")),
                            )

                if "judge" in update:
                    node_state = update["judge"]
                    final_decision = node_state.get("final_decision")
                    if final_decision:
                        await queue.put(
                            format_sse(
                                "judge",
                                {
                                    "thread_id": request.thread_id,
                                    "final_decision": final_decision,
                                    "safety_status": node_state.get("safety_status", "safe"),
                                },
                            )
                        )
                        logger.info(
                            "SSE event queued event=judge thread_id=%s reasons=%s risks=%s",
                            request.thread_id,
                            len(final_decision.get("reasons", [])),
                            len(final_decision.get("risks", [])),
                        )

            await queue.put(format_sse("done", {"thread_id": request.thread_id}))
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info("DebateGraph stream completed thread_id=%s duration_ms=%.1f", request.thread_id, duration_ms)
        except Exception as exc:
            logger.exception("DebateGraph stream failed for thread_id=%s: %s", request.thread_id, exc)
            response = build_api_failure_response(request.thread_id, request.message)
            await queue.put(
                format_sse(
                    "error",
                    {
                        "thread_id": request.thread_id,
                        "final_decision": response.final_decision.model_dump()
                        if response.final_decision
                        else None,
                        "safety_status": response.safety_status,
                    },
                )
            )
            await queue.put(format_sse("done", {"thread_id": request.thread_id}))

    producer = asyncio.create_task(produce_events())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=STREAM_HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield format_sse("heartbeat", {"thread_id": request.thread_id})
                continue

            yield event
            if event.startswith("event: done"):
                break
    finally:
        if not producer.done():
            producer.cancel()


def build_stream_events(response: ChatResponse, failed: bool = False) -> list[str]:
    """ChatResponse를 프론트엔드 순차 렌더링용 SSE 이벤트 목록으로 변환한다."""
    thread_id = response.thread_id
    events = []

    if failed:
        events.append(
            format_sse(
                "error",
                {
                    "thread_id": thread_id,
                    "final_decision": response.final_decision.model_dump()
                    if response.final_decision
                    else None,
                    "safety_status": response.safety_status,
                },
            )
        )
        events.append(format_sse("done", {"thread_id": thread_id}))
        return events

    events.append(
        format_sse(
            "moderator",
            {
                "thread_id": thread_id,
                "normalized_problem": response.normalized_problem.model_dump(),
                "needs_clarification": response.needs_clarification,
                "clarification_questions": response.clarification_questions,
                "safety_status": response.safety_status,
            },
        )
    )

    for turn in response.debate_log:
        payload = turn.model_dump()
        payload["thread_id"] = thread_id
        events.append(format_sse("debater", payload))

    if response.final_decision is not None:
        events.append(
            format_sse(
                "judge",
                {
                    "thread_id": thread_id,
                    "final_decision": response.final_decision.model_dump(),
                    "safety_status": response.safety_status,
                },
            )
        )

    events.append(format_sse("done", {"thread_id": thread_id}))
    return events


@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """DebateGraph를 끝까지 실행하고 전체 토론 결과를 한 번에 반환한다."""
    logger.info("POST /chat/sync received thread_id=%s", request.thread_id)
    response, _ = await run_debate_graph(request)
    return response


@router.post("/chat")
async def chat_stream(request: ChatRequest):
    """SSE 이벤트로 moderator, debater, judge, done 순서의 결과를 전송한다."""
    logger.info("POST /chat stream received thread_id=%s", request.thread_id)
    return StreamingResponse(
        stream_debate_graph(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
