import html
import re
import uuid
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from api import call_backend_stream, BACKEND_URL

# ── Agent 설정 ────────────────────────────────────────────────────────────────

AGENTS = {
    "moderator":   {"name": "Moderator",     "initial": "M", "color": "#5a8fd4", "bg": "rgba(90,143,212,0.12)",  "desc": "고민 구조화 및 라운드 관리"},
    "realist":     {"name": "현실주의자",    "initial": "R", "color": "#3b9e75", "bg": "rgba(59,158,117,0.12)",  "desc": "실현 가능성 · 단기 비용/수익 중심"},
    "idealist":    {"name": "이상주의자",    "initial": "I", "color": "#c27bd4", "bg": "rgba(194,123,212,0.12)", "desc": "장기 가치 · 성장 · 의미 · 만족도"},
    "risk_averse": {"name": "리스크 회피형", "initial": "A", "color": "#d97742", "bg": "rgba(217,119,66,0.12)",  "desc": "최악 시나리오 · 안정성 · 회복 가능성"},
    "judge":       {"name": "Judge",         "initial": "J", "color": "#e6c84a", "bg": "rgba(230,200,74,0.12)",  "desc": "종합 분석 → 최종 결론 도출"},
}

SCENARIOS = [
    {
        "label": "취업 선택",
        "text": (
            "중견기업에는 최종 합격했고, 대기업은 최종 면접을 앞두고 있어.\n"
            "중견기업은 안정적이지만 성장 가능성이 조금 아쉽고,\n"
            "대기업은 붙으면 좋지만 떨어질 가능성도 있어.\n"
            "어떤 선택을 해야 할까?"
        ),
    },
    {
        "label": "휴학 vs 졸업",
        "text": (
            "대학교 3학년인데 이번 학기에 휴학하고 인턴을 할지,\n"
            "그냥 졸업까지 마칠지 고민이야.\n"
            "인턴은 개발 직무와 관련 있지만 아직 확정된 건 아니야."
        ),
    },
]


# ── Session State ─────────────────────────────────────────────────────────────

def init_session():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = None
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""

def new_conversation():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.input_text = ""

_CSS = (Path(__file__).parent / "style.css").read_text()

def _inject_css():
    st.html(f"<style>{_CSS}</style>")

def icon(name: str, size: int = 18) -> str:
    return f'<span class="material-symbols-outlined" style="font-size:{size}px">{name}</span>'


def auto_scroll():
    if "_scroll_seq" not in st.session_state:
        st.session_state._scroll_seq = 0
    st.session_state._scroll_seq += 1
    marker_id = f"stream-scroll-anchor-{st.session_state._scroll_seq}"

    st.markdown(f'<div id="{marker_id}" style="height:1px"></div>', unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        const scrollToLatest = () => {{
          const doc = window.parent.document;
          const marker = doc.getElementById("{marker_id}");
          if (marker) {{
            marker.scrollIntoView({{ behavior: "smooth", block: "end" }});
          }}

          const containers = [
            doc.querySelector('[data-testid="stAppViewContainer"]'),
            doc.querySelector('section.main'),
            doc.scrollingElement,
            doc.documentElement,
            doc.body
          ].filter(Boolean);

          for (const el of containers) {{
            try {{
              el.scrollTo({{ top: el.scrollHeight, behavior: "smooth" }});
            }} catch (error) {{}}
          }}
        }};
        window.setTimeout(scrollToLatest, 80);
        window.setTimeout(scrollToLatest, 280);
        </script>
        """,
        height=1,
    )


# ── 렌더링 ────────────────────────────────────────────────────────────────────

def render_progress(result: dict):
    steps = ["고민 분석", "1라운드", "2라운드", "결론 도출"]
    completed = set()
    if result.get("normalized_problem"):
        completed.add(0)
    for turn in result.get("debate_log", []):
        completed.add(turn["round"])
    if result.get("final_decision"):
        completed.add(3)

    cols = st.columns(4)
    for i, (col, label) in enumerate(zip(cols, steps)):
        if i in completed:
            ic = icon("check_circle", 16)
            color = "inherit"
            weight = "600"
        else:
            ic = icon("radio_button_unchecked", 16)
            color = "#bbb"
            weight = "400"
        col.html(
            f'<div style="text-align:center;color:{color};font-size:12px;font-weight:{weight}">'
            f'{ic}&nbsp;{label}</div>'
        )


def render_round_divider(label: str):
    st.html(
        f'<div style="display:flex;align-items:center;gap:10px;margin:28px 0 16px">'
        f'<div style="flex:1;height:1px;background:rgba(128,128,128,0.2)"></div>'
        f'<span style="font-size:12px;color:#999;letter-spacing:0.5px">{label}</span>'
        f'<div style="flex:1;height:1px;background:rgba(128,128,128,0.2)"></div>'
        f'</div>'
    )


def render_phase_banner(kind: str, label: str, title: str, icon_name: str):
    st.html(
        f'<div class="phase-banner {kind}">'
        f'<div class="phase-icon">{icon(icon_name, 18)}</div>'
        f'<div class="phase-copy">'
        f'<div class="phase-label">{html.escape(label)}</div>'
        f'<div class="phase-title">{html.escape(title)}</div>'
        f'</div>'
        f'</div>'
    )


def message_bubble(agent_key: str, content: str) -> str:
    a = AGENTS.get(agent_key, {"name": agent_key, "initial": "?", "color": "#888", "bg": "rgba(136,136,136,0.12)"})
    safe = html.escape(content)
    safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
    safe = safe.replace('\n', '<br>')
    return (
        f'<div style="display:flex;gap:14px;margin-bottom:16px">'
        f'<div style="width:32px;height:32px;border-radius:50%;background:{a["bg"]};border:1.5px solid {a["color"]};'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:12px;font-weight:700;color:{a["color"]};flex-shrink:0;margin-top:1px">{a["initial"]}</div>'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:13px;font-weight:600;color:{a["color"]};margin-bottom:5px;letter-spacing:0.2px">{a["name"]}</div>'
        f'<div style="border:1px solid {a["color"]}28;border-radius:2px 10px 10px 10px;'
        f'padding:11px 15px;font-size:13.5px;line-height:1.8;word-break:keep-all">{safe}</div>'
        f'</div></div>'
    )


def render_normalized_problem(problem: dict):
    lines = []
    if summary := problem.get("summary"):
        lines.append(summary)
    if options := problem.get("options"):
        lines.append("\n**선택지**")
        lines.extend(f"- {o}" for o in options)
    if criteria := problem.get("criteria"):
        lines.append("\n**판단 기준**")
        lines.extend(f"- {c}" for c in criteria)
    if lines:
        render_round_divider("고민 분석")
        st.html(message_bubble("moderator", "\n".join(lines)))


def render_debate_log(debate_log: list):
    current_round = None
    for turn in debate_log:
        r = turn["round"]
        if r != current_round:
            current_round = r
            if r == 2:
                render_phase_banner("round2", "ROUND SHIFT", "1라운드 의견을 바탕으로 2라운드 반박을 시작합니다", "sync_alt")
            render_round_divider(f"Round {r}")
        content = re.sub(r'^\*\*[^*]+(?:라운드|분석)[^*]*\*\*\s*', '', turn["content"].strip())
        st.html(message_bubble(turn["agent"], content))


def _list_items(items: list) -> str:
    return "".join(
        f'<div class="judge-list-item">'
        f'<span class="judge-bullet">•</span>'
        f'<span>{html.escape(item)}</span>'
        f'</div>'
        for item in items
    )


def render_final_decision(final_decision: dict):
    J = AGENTS["judge"]
    recommendation = html.escape(final_decision.get("recommendation", ""))
    reasons = final_decision.get("reasons", [])
    risks = final_decision.get("risks", [])
    next_action = final_decision.get("next_action")

    next_action_html = (
        f'<div class="judge-next-action">'
        f'<span class="judge-next-label">지금 할 일&nbsp;&nbsp;</span>'
        f'<span class="judge-next-text">{html.escape(next_action)}</span>'
        f'</div>'
        if next_action else ""
    )

    card = f"""
    <div class="judge-card">
      <div class="judge-card-header">
        <div class="judge-avatar">{J["initial"]}</div>
        <div>
          <div class="judge-title">{J["name"]} · 최종 결론</div>
          <div class="judge-sub">2라운드 토론 종합 판단</div>
        </div>
      </div>
      <div class="judge-recommendation">{recommendation}</div>
      <div class="judge-grid">
        <div class="judge-section">
          <div class="judge-section-label">핵심 근거</div>
          {_list_items(reasons)}
        </div>
        <div class="judge-section">
          <div class="judge-section-label">감수할 리스크</div>
          {_list_items(risks)}
        </div>
      </div>
      {next_action_html}
    </div>
    """

    render_round_divider("최종 결론")
    st.html(card)


def empty_result(thread_id: str) -> dict:
    return {
        "thread_id": thread_id,
        "normalized_problem": {},
        "debate_log": [],
        "final_decision": None,
        "needs_clarification": False,
        "clarification_questions": [],
        "safety_status": "safe",
    }


def apply_stream_event(result: dict, event: str, payload: dict) -> dict:
    if event == "moderator":
        result["normalized_problem"] = payload.get("normalized_problem") or {}
        result["needs_clarification"] = payload.get("needs_clarification", False)
        result["clarification_questions"] = payload.get("clarification_questions") or []
        result["safety_status"] = payload.get("safety_status", "safe")
    elif event == "debater":
        result["debate_log"].append(
            {
                "round": payload.get("round", 1),
                "agent": payload.get("agent", ""),
                "stance": payload.get("stance", ""),
                "content": payload.get("content", ""),
                "target": payload.get("target"),
            }
        )
    elif event == "judge":
        result["final_decision"] = payload.get("final_decision")
        result["safety_status"] = payload.get("safety_status", result.get("safety_status", "safe"))
    elif event == "error":
        result["final_decision"] = payload.get("final_decision")
        result["safety_status"] = payload.get("safety_status", result.get("safety_status", "safe"))
    return result


def render_result_body(result: dict, is_streaming: bool = False):
    if result.get("needs_clarification"):
        st.warning("고민을 좀 더 구체적으로 입력해 주세요.")
        for q in result.get("clarification_questions", []):
            st.markdown(f"- {q}")
        return

    if result.get("safety_status") == "unsafe":
        st.error("해당 고민은 안전상의 이유로 토론을 진행할 수 없습니다.")
        if final_decision := result.get("final_decision"):
            render_final_decision(final_decision)
        return

    if problem := result.get("normalized_problem"):
        render_normalized_problem(problem)
    if debate_log := result.get("debate_log"):
        render_debate_log(debate_log)
    if final_decision := result.get("final_decision"):
        render_phase_banner("judge", "JUDGE", "토론을 종합해 최종 결론을 도출했습니다", "gavel")
        render_final_decision(final_decision)
        auto_scroll()
    elif is_streaming and result.get("normalized_problem"):
        if len(result.get("debate_log", [])) >= 6:
            render_phase_banner("judge", "JUDGE", "모든 발언을 종합해 최종 결론을 정리하는 중입니다", "gavel")
            st.info("Judge가 최종 결론을 정리하는 중입니다...")
        else:
            st.info("다음 Agent의 발언을 기다리는 중입니다...")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="고민중계소",
        page_icon="⚖️",
        layout="wide",
        menu_items={"Get Help": None, "Report a bug": None, "About": None},
    )
    init_session()
    _inject_css()

    left, right = st.columns([4, 6], gap="large")

    # ── 왼쪽 ─────────────────────────────────────────────────────────────────
    with left:
        with st.container(border=True):
            st.caption("고민 입력")

            user_input = st.text_area(
                label="고민",
                placeholder="진로, 커리어, 학업 관련 고민을 자유롭게 입력하세요...",
                height=150,
                label_visibility="collapsed",
                value=st.session_state.input_text,
            )

            with st.expander("예시 시나리오"):
                for scenario in SCENARIOS:
                    if st.button(scenario["label"], use_container_width=True, key=f"sc_{scenario['label']}"):
                        st.session_state.input_text = scenario["text"]
                        st.rerun()

            start = st.button("토론 시작하기 →", type="primary", use_container_width=True)

        with st.container(border=True):
            st.caption("참여 에이전트")
            rows = ""
            for key, a in AGENTS.items():
                rows += (
                    f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:14px">'
                    f'<div style="width:9px;height:9px;border-radius:50%;background:{a["color"]};'
                    f'flex-shrink:0;margin-top:6px"></div>'
                    f'<div>'
                    f'<div style="font-size:14px;font-weight:600;color:{a["color"]};'
                    f'margin-bottom:3px;letter-spacing:0.1px">{a["name"]}</div>'
                    f'<div style="font-size:13px;color:#999;line-height:1.4">{a["desc"]}</div>'
                    f'</div></div>'
                )
            st.html(rows)

        if st.session_state.result is not None:
            if st.button("새 대화 시작", use_container_width=True):
                new_conversation()
                st.rerun()

        st.caption("이 서비스는 AI가 생성한 의견입니다. 중요한 결정은 전문가와 반드시 상담하세요.")

    # ── 오른쪽 ────────────────────────────────────────────────────────────────
    with right:
        has_result = st.session_state.result is not None
        result = st.session_state.result or {}

        progress_slot = st.empty()
        body_slot = st.empty()

        with progress_slot.container():
            render_progress(result)
            st.divider()

        if start:
            if not user_input or not user_input.strip():
                st.warning("고민을 입력해주세요.")
            else:
                live_result = empty_result(st.session_state.thread_id)
                st.session_state.result = live_result
                st.session_state.error = None

                try:
                    with body_slot.container():
                        st.info("Moderator가 고민을 분석하는 중입니다...")

                    for event, payload in call_backend_stream(user_input.strip(), st.session_state.thread_id):
                        if event == "done":
                            break

                        live_result = apply_stream_event(live_result, event, payload)

                        with progress_slot.container():
                            render_progress(live_result)
                            st.divider()
                        with body_slot.container():
                            render_result_body(live_result, is_streaming=True)
                            auto_scroll()

                    st.session_state.result = live_result
                    st.session_state.error = None
                except TimeoutError:
                    st.session_state.error = "요청 시간이 초과되었습니다. 다시 시도해 주세요."
                except ConnectionError:
                    st.session_state.error = f"백엔드 서버에 연결할 수 없습니다. ({BACKEND_URL})"
                except Exception:
                    st.session_state.error = "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

                st.rerun()

        if st.session_state.error:
            with body_slot.container():
                st.error(st.session_state.error)
        elif not has_result:
            with body_slot.container():
                st.info("고민을 입력하고 토론을 시작하면 AI 에이전트들의 토론이 여기에 표시됩니다.")
        else:
            with body_slot.container():
                render_result_body(result)


if __name__ == "__main__":
    main()
