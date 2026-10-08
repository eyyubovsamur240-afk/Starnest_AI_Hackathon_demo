"""Escalation Copilot: Streamlit UI.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from copilot import MODEL, analyze, llm_available

ROOT = Path(__file__).parent
# Rough time for an agent to read an escalated chat by hand (measure your own for the pitch).
MANUAL_READ_SECONDS = 90

RISK_COLORS = {"low": "#1f9d55", "medium": "#d97706", "high": "#dc2626"}
SENTIMENT_LABELS = {1: "calm", 2: "mildly annoyed", 3: "annoyed", 4: "angry", 5: "furious"}

st.set_page_config(page_title="Escalation Copilot", page_icon="🛟", layout="wide")


@st.cache_data
def load_tickets() -> list[dict]:
    return json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))


if "time_saved" not in st.session_state:
    st.session_state.time_saved = 0.0
    st.session_state.analyzed = 0

with st.sidebar:
    st.header("Escalation Copilot")
    st.caption("Escalated chat in → summary, churn risk and a ready Azerbaijani reply out.")
    if llm_available():
        st.success(f"Live mode: {MODEL}")
        offline = st.toggle("Force offline mode", value=False, help="Use keyword rules instead of the LLM (Wi-Fi fallback)")
    else:
        st.warning("Offline mode: set GEMINI_API_KEY for real AI analysis.")
        offline = True
    st.divider()
    stats = st.empty()  # filled at the end so it reflects the latest Analyze click
    st.caption(f"Assumes ~{MANUAL_READ_SECONDS}s to read a chat manually.")
    st.divider()
    st.caption("Demo uses synthetic chats only. No real customer data.")

st.title("🛟 Escalation Copilot")
st.write("The bot couldn't solve it. Get full context in one click.")

tickets = load_tickets()
options = ["(paste your own chat)"] + [f"{t['id']} · {t['tone']} · {t['language']}" for t in tickets]
choice = st.selectbox("Sample chat", options, index=min(16, len(options) - 1))
default_chat = "" if choice == options[0] else tickets[options.index(choice) - 1]["chat"]

left, right = st.columns([1, 1], gap="large")

with left:
    chat = st.text_area("Escalated chat", value=default_chat, height=360, key=f"chat_{choice}")
    go = st.button("Analyze", type="primary", use_container_width=True, disabled=not chat.strip())

if go:
    with st.spinner("Reading the chat..."):
        try:
            st.session_state.result = analyze(chat, force_offline=offline)
            st.session_state.time_saved += max(0.0, MANUAL_READ_SECONDS - st.session_state.result.seconds)
            st.session_state.analyzed += 1
        except Exception as exc:
            st.session_state.result = None
            st.error(f"Analysis failed: {exc}. Try 'Force offline mode' in the sidebar.")

result = st.session_state.get("result")
with right:
    if result is None:
        st.info("Pick a sample or paste a chat, then click **Analyze**.")
    else:
        a = result.analysis
        color = RISK_COLORS[a.churn_risk]
        st.markdown(
            f"<div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center'>"
            f"<span style='background:{color};color:white;padding:4px 12px;border-radius:999px;font-weight:600'>"
            f"Churn risk: {a.churn_risk.upper()}</span>"
            f"<span style='border:1px solid #999;padding:4px 12px;border-radius:999px'>{a.category.replace('_', ' ')}</span>"
            f"<span style='border:1px solid #999;padding:4px 12px;border-radius:999px'>"
            f"Sentiment {a.sentiment}/5 · {SENTIMENT_LABELS[a.sentiment]}</span>"
            f"<span style='opacity:.7'>⏱ {result.seconds:.1f}s · {result.mode}</span></div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Why: {a.risk_reason}")

        st.subheader("Summary")
        for line in a.summary.strip().splitlines():
            if line.strip():
                st.markdown(f"- {line.strip()}")

        st.subheader("Next action")
        st.markdown(f"**{a.next_action.replace('_', ' ').title()}**")

        st.subheader("Suggested reply (AZ)")
        reply = st.text_area("Edit before sending", value=a.suggested_reply_az, height=140, key=f"reply_{id(result)}")
        st.code(reply, language=None)
        st.caption("Use the copy icon on the box above to copy the reply.")

with stats.container():
    st.metric("Chats analyzed", st.session_state.analyzed)
    st.metric("Agent time saved", f"{st.session_state.time_saved / 60:.1f} min")
