"""Escalation Copilot: Streamlit UI (Azerbaijani).

Run with:  python -m streamlit run app.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from copilot import MODEL, analyze, llm_available
from labels_az import ACTION, ACTION_ICON, CATEGORY, LANGUAGE, RISK, SENTIMENT, TONE

ROOT = Path(__file__).parent
# Rough time for an agent to read an escalated chat by hand (measure your own for the pitch).
MANUAL_READ_SECONDS = 90

RISK_COLORS = {"low": "#16a34a", "medium": "#d97706", "high": "#dc2626"}
RISK_BG = {"low": "#f0fdf4", "medium": "#fffbeb", "high": "#fef2f2"}
SENTIMENT_EMOJI = {1: "🙂", 2: "😐", 3: "😕", 4: "😠", 5: "🤬"}

st.set_page_config(page_title="Eskalasiya Köməkçisi", page_icon="🛟", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 3.5rem; max-width: 1200px;}
.hero {background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 55%, #8b5cf6 100%);
       color: #fff; border-radius: 18px; padding: 26px 30px; margin-bottom: 22px;
       box-shadow: 0 10px 30px rgba(109, 40, 217, .25);}
.hero h1 {color: #fff; margin: 0 0 6px 0; font-size: 2rem;}
.hero p {margin: 0; opacity: .9; font-size: 1.05rem;}
.card {background: #fff; border: 1px solid #ece8f5; border-radius: 14px; padding: 16px 18px;
       box-shadow: 0 2px 10px rgba(30, 20, 60, .05); height: 100%;}
.card .label {font-size: .78rem; letter-spacing: .02em; font-weight: 600;
              color: #6b7280; margin-bottom: 6px;}
.card .value {font-size: 1.2rem; font-weight: 700; color: #1f2937;}
.card .sub {font-size: .85rem; color: #6b7280; margin-top: 4px;}
.risk-card {border-width: 2px;}
.section-title {font-weight: 700; font-size: 1.05rem; margin: 18px 0 8px 0; color: #312e81;}
.summary li {margin-bottom: 6px; line-height: 1.45;}
.action {display: flex; align-items: center; gap: 12px; background: #f5f3ff;
         border-left: 5px solid #6d28d9; border-radius: 10px; padding: 12px 16px;
         font-weight: 600; font-size: 1.05rem;}
.reason {background: #f9fafb; border-radius: 10px; padding: 10px 14px; color: #374151;
         font-size: .92rem; margin-top: 10px;}
.pill {display: inline-block; background: #ede9fe; color: #5b21b6; border-radius: 999px;
       padding: 2px 10px; font-size: .8rem; font-weight: 600;}
.empty {border: 2px dashed #ddd6fe; border-radius: 14px; padding: 40px 24px; text-align: center;
        color: #6b7280; background: #faf9ff;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_tickets() -> list[dict]:
    return json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))


def card(label: str, value: str, sub: str = "", style: str = "", extra_class: str = "") -> str:
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='card {extra_class}' style='{style}'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>{sub_html}</div>"
    )


if "time_saved" not in st.session_state:
    st.session_state.time_saved = 0.0
    st.session_state.analyzed = 0

with st.sidebar:
    st.markdown("## 🛟 Eskalasiya Köməkçisi")
    st.caption("Eskalasiya olunmuş söhbət daxil olur, xülasə, müştərini itirmə riski və hazır cavab çıxır.")
    if llm_available():
        st.success(f"Canlı rejim: {MODEL}")
        offline = st.toggle(
            "Oflayn rejim", value=False,
            help="Süni intellekt əvəzinə açar söz qaydalarından istifadə et (internet zəif olanda)",
        )
    else:
        st.warning("Oflayn rejim: real təhlil üçün GEMINI_API_KEY təyin edin.")
        offline = True
    st.divider()
    stats = st.empty()  # filled at the end so it reflects the latest click
    st.caption(f"Bir söhbəti əl ilə oxumaq təxminən {MANUAL_READ_SECONDS} saniyə çəkir.")
    st.divider()
    st.caption("Demo yalnız uydurma söhbətlərdən istifadə edir. Real müştəri məlumatı yoxdur.")

st.markdown(
    "<div class='hero'><h1>🛟 Eskalasiya Köməkçisi</h1>"
    "<p>Bot problemi həll edə bilmədi? Bir kliklə söhbətin tam mənzərəsini alın.</p></div>",
    unsafe_allow_html=True,
)

tickets = load_tickets()
options = ["(öz söhbətinizi yapışdırın)"] + [
    f"{t['id']} · {TONE.get(t['tone'], t['tone'])} · {LANGUAGE.get(t['language'], t['language'])}"
    for t in tickets
]

left, right = st.columns([5, 6], gap="large")

with left:
    with st.container(border=True):
        st.markdown("<div class='section-title' style='margin-top:0'>💬 Söhbət</div>", unsafe_allow_html=True)
        choice = st.selectbox("Nümunə söhbət", options, index=min(16, len(options) - 1))
        default_chat = "" if choice == options[0] else tickets[options.index(choice) - 1]["chat"]
        chat = st.text_area(
            "Eskalasiya olunmuş söhbət", value=default_chat, height=380, key=f"chat_{choice}",
            placeholder="Müştəri ilə botun yazışmasını bura yapışdırın...",
        )
        go = st.button("🔍 Təhlil et", type="primary", use_container_width=True, disabled=not chat.strip())

if go:
    with st.spinner("Söhbət oxunur..."):
        try:
            st.session_state.result = analyze(chat, force_offline=offline)
            st.session_state.time_saved += max(0.0, MANUAL_READ_SECONDS - st.session_state.result.seconds)
            st.session_state.analyzed += 1
        except Exception as exc:
            st.session_state.result = None
            st.error(f"Təhlil alınmadı: {exc}. Yan paneldə \"Oflayn rejim\"i yoxlayın.")

result = st.session_state.get("result")
with right:
    if result is None:
        st.markdown(
            "<div class='empty'><div style='font-size:2.2rem'>🧭</div>"
            "<div style='font-weight:600;margin:6px 0'>Nəticə burada görünəcək</div>"
            "Nümunə seçin və ya söhbəti yapışdırın, sonra <b>Təhlil et</b> düyməsini basın.</div>",
            unsafe_allow_html=True,
        )
    else:
        a = result.analysis
        color = RISK_COLORS[a.churn_risk]
        mode = "süni intellekt" if result.mode == "llm" else "oflayn"

        c1, c2, c3 = st.columns(3)
        c1.markdown(
            card("Müştərini itirmə riski", f"<span style='color:{color}'>{RISK[a.churn_risk]}</span>",
                 style=f"border-color:{color};background:{RISK_BG[a.churn_risk]}", extra_class="risk-card"),
            unsafe_allow_html=True,
        )
        c2.markdown(card("Kateqoriya", CATEGORY[a.category]), unsafe_allow_html=True)
        c3.markdown(
            card("Əhval", f"{SENTIMENT_EMOJI[a.sentiment]} {a.sentiment}/5", SENTIMENT[a.sentiment]),
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='reason'><b>Səbəb:</b> {html.escape(a.risk_reason)}</div>"
            f"<div style='margin-top:8px'><span class='pill'>⏱ {result.seconds:.1f} san · {mode}</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='section-title'>📝 Xülasə</div>", unsafe_allow_html=True)
        lines = [l.strip() for l in a.summary.strip().splitlines() if l.strip()]
        st.markdown(
            "<ul class='summary'>" + "".join(f"<li>{html.escape(l)}</li>" for l in lines) + "</ul>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='section-title'>➡️ Növbəti addım</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='action'><span style='font-size:1.4rem'>{ACTION_ICON[a.next_action]}</span>"
            f"{ACTION[a.next_action]}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='section-title'>✉️ Təklif olunan cavab</div>", unsafe_allow_html=True)
        reply = st.text_area(
            "Göndərməzdən əvvəl redaktə edin", value=a.suggested_reply_az, height=140, key=f"reply_{id(result)}"
        )
        st.code(reply, language=None)
        st.caption("Cavabı kopyalamaq üçün yuxarıdakı qutunun küncündəki ikona basın.")

with stats.container():
    s1, s2 = st.columns(2)
    s1.metric("Təhlil edilib", st.session_state.analyzed)
    s2.metric("Qənaət", f"{st.session_state.time_saved / 60:.1f} dəq")
