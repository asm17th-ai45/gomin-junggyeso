import html
import re
import uuid
import streamlit as st
from api import call_backend_sync, BACKEND_URL

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

MATERIAL_ICONS_CDN = """
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,300,0,0" rel="stylesheet"/>
<style>
  .material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 300, 'OPSZ' 24;
    vertical-align: middle;
    line-height: 1;
  }
</style>
"""

def icon(name: str, size: int = 18) -> str:
    return f'<span class="material-symbols-outlined" style="font-size:{size}px">{name}</span>'


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
        col.markdown(
            f'<div style="text-align:center;color:{color};font-size:12px;font-weight:{weight}">'
            f'{ic}&nbsp;{label}</div>',
            unsafe_allow_html=True,
        )


def render_round_divider(label: str):
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin:28px 0 16px">'
        f'<div style="flex:1;height:1px;background:rgba(128,128,128,0.2)"></div>'
        f'<span style="font-size:12px;color:#999;letter-spacing:0.5px">{label}</span>'
        f'<div style="flex:1;height:1px;background:rgba(128,128,128,0.2)"></div>'
        f'</div>',
        unsafe_allow_html=True,
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
        st.markdown(message_bubble("moderator", "\n".join(lines)), unsafe_allow_html=True)



def render_debate_log(debate_log: list):
    current_round = None
    for turn in debate_log:
        r = turn["round"]
        if r != current_round:
            current_round = r
            render_round_divider(f"Round {r}")
        content = re.sub(r'^\*\*[^*]+(?:라운드|분석)[^*]*\*\*\s*', '', turn["content"].strip())
        st.markdown(message_bubble(turn["agent"], content), unsafe_allow_html=True)


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="고민중계소",
        page_icon="⚖️",
        layout="wide",
        menu_items={"Get Help": None, "Report a bug": None, "About": None},
    )
    init_session()
    st.markdown(MATERIAL_ICONS_CDN, unsafe_allow_html=True)

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
            st.markdown(rows, unsafe_allow_html=True)

        if st.session_state.result is not None:
            if st.button("새 대화 시작", use_container_width=True):
                new_conversation()
                st.rerun()

        st.caption("이 서비스는 AI가 생성한 의견입니다. 중요한 결정은 전문가와 반드시 상담하세요.")

    # ── 오른쪽 ────────────────────────────────────────────────────────────────
    with right:
        has_result = st.session_state.result is not None
        result = st.session_state.result or {}

        render_progress(result)
        st.divider()

        if start:
            if not user_input or not user_input.strip():
                st.warning("고민을 입력해주세요.")
            else:
                with st.spinner("AI들이 토론 중입니다..."):
                    try:
                        res = call_backend_sync(user_input.strip(), st.session_state.thread_id)
                        st.session_state.result = res
                        st.session_state.error = None
                    except TimeoutError:
                        st.session_state.error = "요청 시간이 초과되었습니다. 다시 시도해 주세요."
                    except ConnectionError:
                        st.session_state.error = f"백엔드 서버에 연결할 수 없습니다. ({BACKEND_URL})"
                    except Exception:
                        st.session_state.error = "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
                st.rerun()

        if st.session_state.error:
            st.error(st.session_state.error)
        elif not has_result:
            st.info("고민을 입력하고 토론을 시작하면 AI 에이전트들의 토론이 여기에 표시됩니다.")
        else:
            if needs_clarification := result.get("needs_clarification"):
                st.warning("고민을 좀 더 구체적으로 입력해 주세요.")
                for q in result.get("clarification_questions", []):
                    st.markdown(f"- {q}")
            elif result.get("safety_status") == "unsafe":
                st.error("해당 고민은 안전상의 이유로 토론을 진행할 수 없습니다.")
            else:
                if problem := result.get("normalized_problem"):
                    render_normalized_problem(problem)
                if debate_log := result.get("debate_log"):
                    render_debate_log(debate_log)


if __name__ == "__main__":
    main()
