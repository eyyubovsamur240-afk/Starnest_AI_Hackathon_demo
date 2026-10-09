"""Escalation Copilot: Streamlit UI (Azerbaijani).

Main screen: the bot <-> customer chat on the left, the analysis on the right,
and the AI accuracy block underneath.

Run with:  python -m streamlit run app.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from copilot import QuotaError, SetupError, analyze
from copilot_ui import gemini_problem_az, mode_sidebar, nav, source_badge
from labels_az import CATEGORY, LANGUAGE, RISK, SENTIMENT, TONE

ROOT = Path(__file__).parent

RISK_COLORS = {"low": "#16a34a", "medium": "#d97706", "high": "#dc2626"}
RISK_BG = {"low": "#f0fdf4", "medium": "#fffbeb", "high": "#fef2f2"}
SENTIMENT_EMOJI = {1: "🙂", 2: "😐", 3: "😕", 4: "😠", 5: "🤬"}
CUSTOMER_PREFIXES = ("customer", "müştəri", "клиент")

st.set_page_config(page_title="Eskalasiya Köməkçisi", page_icon="🛟", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 3rem; max-width: 1250px;}
.hero {background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 55%, #8b5cf6 100%);
       color: #fff; border-radius: 16px; padding: 18px 26px; margin-bottom: 18px;}
.hero h1 {color: #fff; margin: 0; font-size: 1.7rem;}
.hero p {margin: 4px 0 0 0; opacity: .9;}
.col-title {font-weight: 700; font-size: 1.1rem; color: #312e81; margin-bottom: 8px;}
.chat {display: flex; flex-direction: column; gap: 8px; max-height: 470px; overflow-y: auto;
       padding: 4px 2px;}
.msg {max-width: 82%; padding: 8px 12px; border-radius: 14px; line-height: 1.4; font-size: .95rem;}
.msg .who {font-size: .72rem; font-weight: 700; opacity: .7; margin-bottom: 2px;}
.msg.customer {align-self: flex-start; background: #f3f4f6; color: #111827; border-bottom-left-radius: 4px;}
.msg.bot {align-self: flex-end; background: #ede9fe; color: #3b0764; border-bottom-right-radius: 4px;}
.card {background: #fff; border: 1px solid #ece8f5; border-radius: 12px; padding: 12px 16px;
       margin-bottom: 10px;}
.card .label {font-size: .78rem; font-weight: 600; color: #6b7280; margin-bottom: 4px;}
.card .value {font-size: 1.15rem; font-weight: 700; color: #1f2937;}
.card .sub {font-size: .85rem; color: #6b7280; margin-top: 2px;}
.card ul {margin: 0; padding-left: 18px;}
.card li {margin-bottom: 4px; line-height: 1.4;}
.empty {border: 2px dashed #ddd6fe; border-radius: 14px; padding: 36px 20px; text-align: center;
        color: #6b7280; background: #faf9ff;}
.acc-title {font-weight: 700; font-size: 1.15rem; color: #312e81; margin: 26px 0 10px 0;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_tickets() -> list[dict]:
    return json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))


def load_eval() -> dict | None:
    """Latest eval.py summary: the LLM run if it exists, otherwise the offline baseline."""
    for mode in ("llm", "offline"):
        path = ROOT / "results" / f"eval_{mode}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["summary"]
    return None


def card(label: str, value: str, sub: str = "", style: str = "") -> str:
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='card' style='{style}'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>{sub_html}</div>"
    )


def chat_bubbles(chat: str) -> str:
    """Render 'Customer: ...' / 'Bot: ...' lines as chat bubbles."""
    parts = []
    for line in chat.strip().splitlines():
        if not line.strip():
            continue
        speaker, sep, text = line.partition(":")
        if sep and speaker.strip().lower() in CUSTOMER_PREFIXES:
            who, cls = "Müştəri", "customer"
        elif sep and speaker.strip().lower() == "bot":
            who, cls = "Bot", "bot"
        else:
            who, cls, text = "", "customer", line
        who_html = f"<div class='who'>{who}</div>" if who else ""
        parts.append(f"<div class='msg {cls}'>{who_html}{html.escape(text.strip())}</div>")
    return "<div class='chat'>" + "".join(parts) + "</div>"


for key, default in (("reply_ratings", {}), ("summary_ratings", {}), ("result", None)):
    st.session_state.setdefault(key, default)

with st.sidebar:
    st.markdown("## 🛟 Eskalasiya Köməkçisi")
    nav()  # links to the queue and statistics pages
    st.divider()
    offline = mode_sidebar()
    st.caption("Demo yalnız uydurma söhbətlərdən istifadə edir.")

st.markdown(
    "<div class='hero'><h1>🛟 Eskalasiya Köməkçisi</h1>"
    "<p>Botun həll edə bilmədiyi söhbət, bir baxışda.</p></div>",
    unsafe_allow_html=True,
)

tickets = load_tickets()
options = ["(öz söhbətinizi yapışdırın)"] + [
    f"{t['id']} · {TONE.get(t['tone'], t['tone'])} · {LANGUAGE.get(t['language'], t['language'])}"
    for t in tickets
]

left, right = st.columns(2, gap="large")

# --- Left: customer conversation -------------------------------------------
with left:
    with st.container(border=True):
        st.markdown("<div class='col-title'>💬 Müştəri söhbəti</div>", unsafe_allow_html=True)
        choice = st.selectbox("Söhbət", options, index=min(16, len(options) - 1), label_visibility="collapsed")
        if choice == options[0]:
            chat = st.text_area(
                "Söhbət", height=420, key="own_chat", label_visibility="collapsed",
                placeholder="Bot ilə müştərinin yazışmasını bura yapışdırın...\nMüştəri: ...\nBot: ...",
            )
        else:
            sample = tickets[options.index(choice) - 1]
            chat = sample["chat"]
            st.markdown(chat_bubbles(chat), unsafe_allow_html=True)

# --- Right: analysis ---------------------------------------------------------
with right:
    with st.container(border=True):
        st.markdown("<div class='col-title'>🔍 Təhlil</div>", unsafe_allow_html=True)
        if st.button("Təhlil et", type="primary", width="stretch", disabled=not chat.strip()):
            with st.spinner("Söhbət oxunur..."):
                try:
                    # The sample's CRM name is masked too, so it never reaches Gemini.
                    names = [sample["customer"]["name"]] if choice != options[0] else None
                    try:  # a saved Gemini answer is used first, so sample chats cost no quota
                        st.session_state.result = analyze(chat, force_offline=offline, known_names=names)
                    except (QuotaError, SetupError) as exc:
                        st.warning(gemini_problem_az(exc))
                        st.session_state.result = analyze(chat, force_offline=True, known_names=names)
                    st.session_state.result_chat = chat
                except Exception as exc:
                    st.session_state.result = None
                    st.error(f"Təhlil alınmadı: {exc}. Yan paneldə \"Oflayn rejim\"i yoxlayın.")

        # Hide an old result once a different chat is selected.
        result = st.session_state.result if st.session_state.get("result_chat") == chat else None
        if result is None:
            st.markdown(
                "<div class='empty'><div style='font-size:2rem'>🧭</div>"
                "Söhbəti seçin və <b>Təhlil et</b> düyməsini basın.</div>",
                unsafe_allow_html=True,
            )
        else:
            a = result.analysis
            rid = str(id(result))
            st.markdown(source_badge(result), unsafe_allow_html=True)
            lines = [l.strip() for l in a.summary.strip().splitlines() if l.strip()]
            st.markdown(
                card("Xülasə", "<ul style='font-size:.95rem;font-weight:500'>"
                     + "".join(f"<li>{html.escape(l)}</li>" for l in lines) + "</ul>"),
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            c1.markdown(
                card("Əhval", f"{SENTIMENT_EMOJI[a.sentiment]} {a.sentiment}/5", SENTIMENT[a.sentiment]),
                unsafe_allow_html=True,
            )
            color = RISK_COLORS[a.churn_risk]
            c2.markdown(
                card("Müştərini itirmə riski", f"<span style='color:{color}'>{RISK[a.churn_risk]}</span>",
                     style=f"border:2px solid {color};background:{RISK_BG[a.churn_risk]}"),
                unsafe_allow_html=True,
            )
            c3.markdown(card("Problem kateqoriyası", CATEGORY[a.category]), unsafe_allow_html=True)

            st.markdown("<div class='card' style='border:none;padding:4px 2px;margin:0'>"
                        "<div class='label'>Təklif olunan cavab</div></div>", unsafe_allow_html=True)
            st.text_area("Təklif olunan cavab", value=a.suggested_reply_az, height=130,
                         key=f"reply_{rid}", label_visibility="collapsed")

            r1, r2 = st.columns(2)
            with r1:
                st.caption("Xülasə dəqiqdir?")
                s = st.feedback("thumbs", key=f"sum_fb_{rid}")
                if s is not None:
                    st.session_state.summary_ratings[rid] = s
            with r2:
                st.caption("Cavabın keyfiyyəti")
                r = st.feedback("stars", key=f"reply_fb_{rid}")
                if r is not None:
                    st.session_state.reply_ratings[rid] = r + 1

# --- Below: AI accuracy -------------------------------------------------------
st.markdown("<div class='acc-title'>📊 AI dəqiqliyi</div>", unsafe_allow_html=True)
ev = load_eval()
sums = list(st.session_state.summary_ratings.values())
stars = list(st.session_state.reply_ratings.values())

m1, m2, m3, m4 = st.columns(4)
with m1:
    if sums:
        m1.metric("Xülasə", f"{round(100 * sum(sums) / len(sums))}% 👍", help="İnsan qiymətləndirməsi")
        st.caption(f"{len(sums)} xülasə yoxlanılıb")
    else:
        m1.metric("Xülasə", "—", help="İnsan qiymətləndirməsi")
        st.caption("Təhlildən sonra 👍/👎 ilə qiymətləndirin")
with m2:
    m2.metric("Kateqoriya", f"{ev['category_accuracy']:.0f}%" if ev else "—")
with m3:
    m3.metric("Əhval", f"{ev['sentiment_within_1']:.0f}%" if ev else "—", help="±1 bal fərqlə düzgün")
with m4:
    if stars:
        m4.metric("Cavab keyfiyyəti", f"{sum(stars) / len(stars):.1f} / 5 ⭐", help="İnsan qiymətləndirməsi")
        st.caption(f"{len(stars)} cavab qiymətləndirilib")
    else:
        m4.metric("Cavab keyfiyyəti", "—", help="İnsan qiymətləndirməsi")
        st.caption("Təhlildən sonra ulduzla qiymətləndirin")

if ev and ev["mode"] == "llm":
    part = f" (qismən: {ev['tickets_in_set']} söhbətdən {ev['tickets']})" if ev.get("partial") else ""
    st.caption(f"Kateqoriya və əhval: Gemini, {ev['tickets']} uydurma söhbət üzrə eval.py nəticəsi{part}.")
elif ev:
    st.caption(f"Kateqoriya və əhval: {ev['tickets']} uydurma söhbət üzrə **oflayn açar söz qaydalarının** nəticəsi, "
               "Gemini-nin yox. Gemini-ni yoxlamaq üçün açarla `python eval.py` işə salın.")
else:
    st.caption("Kateqoriya və əhval üçün əvvəlcə `python eval.py` işə salın.")
