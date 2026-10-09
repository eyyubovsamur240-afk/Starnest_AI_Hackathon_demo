"""Shared pieces for the extra pages (pages/): styles, chat bubbles, the analysis
panel, the priority queue and charts. The main screen lives in app.py."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from copilot import MODEL, analyze, llm_available
from labels_az import (
    ACTION,
    ACTION_ICON,
    BOT_FAILURE,
    BOT_FAILURE_FIX,
    BOT_FAILURE_ICON,
    CATEGORY,
    RISK,
    SENTIMENT,
)
from offers import suggest
from privacy import describe

ROOT = Path(__file__).parent

BRAND = "#6d28d9"
RISK_COLORS = {"low": "#16a34a", "medium": "#d97706", "high": "#dc2626"}
RISK_BG = {"low": "#f0fdf4", "medium": "#fffbeb", "high": "#fef2f2"}
RISK_DOT = {"low": "🟢", "medium": "🟠", "high": "🔴"}
RISK_WEIGHT = {"low": 100, "medium": 200, "high": 300}
SENTIMENT_EMOJI = {1: "🙂", 2: "😐", 3: "😕", 4: "😠", 5: "🤬"}
MODE_LABEL = {"llm": "🤖 Gemini", "cache": "🤖 Gemini · yaddaşdan", "offline": "⚙️ Oflayn qaydalar"}

PAGES = [
    ("app.py", "Söhbət təhlili", "🔍"),
    ("pages/1_queue.py", "Prioritet növbəsi", "📥"),
    ("pages/2_stats.py", "Statistika", "📈"),
]

CSS = """
<style>
.block-container {padding-top: 3.5rem; max-width: 1280px;}
.hero {background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 55%, #8b5cf6 100%);
       color: #fff; border-radius: 18px; padding: 22px 28px; margin-bottom: 14px;
       box-shadow: 0 10px 30px rgba(109, 40, 217, .25);}
.hero h1 {color: #fff; margin: 0 0 4px 0; font-size: 1.9rem;}
.hero p {margin: 0; opacity: .92; font-size: 1.02rem;}
.card {background: #fff; border: 1px solid #ece8f5; border-radius: 14px; padding: 14px 16px;
       box-shadow: 0 2px 10px rgba(30, 20, 60, .05); height: 100%;}
.card .label {font-size: .78rem; letter-spacing: .02em; font-weight: 600; color: #6b7280; margin-bottom: 6px;}
.card .value {font-size: 1.2rem; font-weight: 700; color: #1f2937;}
.card .sub {font-size: .85rem; color: #6b7280; margin-top: 4px;}
.risk-card {border-width: 2px;}
.section-title {font-weight: 700; font-size: 1.02rem; margin: 18px 0 8px 0; color: #312e81;}
.summary li {margin-bottom: 6px; line-height: 1.45;}
.action {display: flex; align-items: center; gap: 12px; background: #f5f3ff;
         border-left: 5px solid #6d28d9; border-radius: 10px; padding: 12px 16px;
         font-weight: 600; font-size: 1.02rem;}
.reason {background: #f9fafb; border-radius: 10px; padding: 10px 14px; color: #374151;
         font-size: .92rem; margin-top: 10px;}
.pill {display: inline-block; background: #ede9fe; color: #5b21b6; border-radius: 999px;
       padding: 2px 10px; font-size: .8rem; font-weight: 600; margin: 6px 6px 0 0;}
.pill.privacy {background: #ecfdf5; color: #047857;}
.empty {border: 2px dashed #ddd6fe; border-radius: 14px; padding: 36px 24px; text-align: center;
        color: #6b7280; background: #faf9ff;}
.box {border-radius: 12px; padding: 12px 16px; margin-top: 4px; font-size: .93rem; line-height: 1.45;}
.box.fail {background: #fff7ed; border: 1px solid #fed7aa;}
.box.faq {background: #f8fafc; border: 1px solid #e2e8f0; margin-top: 8px;}
.box.offer {background: #f0fdf4; border: 1px solid #bbf7d0;}
.box.nooffer {background: #f9fafb; border: 1px solid #e5e7eb; color: #6b7280;}
.box b.t {display: block; margin-bottom: 4px; color: #1f2937;}
.muted {color: #6b7280; font-size: .85rem;}
.chat {display: flex; flex-direction: column; background: #fff; border: 1px solid #ece8f5;
       border-radius: 14px; padding: 12px 14px; max-height: 460px; overflow-y: auto;}
.msg {max-width: 86%; padding: 8px 12px; border-radius: 12px; margin: 4px 0; font-size: .9rem; line-height: 1.4;}
.msg .who {font-size: .7rem; font-weight: 700; color: #6b7280; margin-bottom: 2px;}
.msg.cust {background: #f3f4f6; color: #111827; margin-right: auto; border-bottom-left-radius: 4px;}
.msg.bot {background: #ede9fe; color: #3b0764; margin-left: auto; border-bottom-right-radius: 4px;}
.msg.handoff {background: #fff7ed; border: 1px dashed #fb923c; margin: 8px auto 0 auto; text-align: center;}
.mask {background: #d1fae5; color: #065f46; border-radius: 4px; padding: 0 3px; font-weight: 600;}
.profile {background: #fff; border: 1px solid #ece8f5; border-radius: 14px; padding: 12px 16px; margin-bottom: 10px;}
.profile .name {font-weight: 700; font-size: 1.05rem; color: #1f2937;}
.profile .row {font-size: .88rem; color: #374151; margin-top: 3px;}
.col-title {font-weight: 700; font-size: 1.1rem; color: #312e81; margin-bottom: 8px;}
.acc-title {font-weight: 700; font-size: 1.15rem; color: #312e81; margin: 26px 0 10px 0;}
.card ul {margin: 0; padding-left: 18px;}
.card li {margin-bottom: 4px; line-height: 1.4;}
</style>
"""


def nav() -> None:
    """Sidebar links between the pages, with Azerbaijani names."""
    for path, label, icon in PAGES:
        st.page_link(path, label=label, icon=icon)


def setup_page(title: str) -> bool:
    """Page config, styles and sidebar. Returns True when the app runs offline."""
    st.set_page_config(page_title=f"{title} · Eskalasiya Köməkçisi", page_icon="🛟", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("## 🛟 Eskalasiya Köməkçisi")
        nav()
        st.divider()
        if llm_available():
            st.success(f"Canlı rejim: {MODEL}")
            offline = st.toggle("Oflayn rejim", value=False, help="Süni intellekt əvəzinə açar söz qaydaları")
        else:
            st.warning("Oflayn rejim: real təhlil üçün GEMINI_API_KEY təyin edin.")
            offline = True
        st.caption("🔒 Telefon, ad, kart, e-poçt və FİN kod süni intellektə göndərilməzdən əvvəl gizlədilir.")
        st.caption("Demo yalnız uydurma söhbət və profillərdən istifadə edir.")
    st.markdown(f"<div class='hero'><h1>{title}</h1></div>", unsafe_allow_html=True)
    return offline


def ensure_queue(tickets: list[dict], offline: bool) -> None:
    """Without an API key the whole queue is analyzed instantly with the offline rules."""
    if "queue" not in st.session_state and offline:
        run_queue(tickets, offline=True)


@st.cache_data
def load_tickets() -> list[dict]:
    return json.loads((ROOT / "data" / "tickets.json").read_text(encoding="utf-8"))


def source_badge(result) -> str:
    """Who decided the category, risk, sentiment and bot-failure reason for this result.
    Inline styles so it looks the same on the main screen, which has its own CSS."""
    style = ("display:inline-block;border-radius:999px;padding:3px 12px;font-size:.82rem;"
             "font-weight:600;margin:0 6px 8px 0;")
    if result.mode == "offline":
        return (f"<span style='{style}background:#fef3c7;color:#92400e'>"
                "⚙️ Oflayn açar söz qaydaları · Gemini istifadə olunmayıb</span>")
    when = "yaddaşdan" if result.mode == "cache" else f"{result.seconds:.1f} san"
    return f"<span style='{style}background:#ede9fe;color:#5b21b6'>🤖 Gemini ({MODEL}) qərar verdi · {when}</span>"


def card(label: str, value: str, sub: str = "", style: str = "", extra_class: str = "") -> str:
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='card {extra_class}' style='{style}'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>{sub_html}</div>"
    )


def esc(text: str) -> str:
    return html.escape(text)


def highlight_masks(escaped: str) -> str:
    return re.sub(r"\[(TELEFON|AD|KART|EMAIL|FİN)\]", r"<span class='mask'>[\1]</span>", escaped)


def is_handoff(line: str) -> bool:
    low = line.lower()
    return low.startswith("bot:") and any(w in low for w in ("operator", "оператор", "agent"))


def render_chat(text: str) -> None:
    """Show the bot-customer chat as message bubbles, the handoff line at the bottom."""
    parts = []
    for line in [l.strip() for l in text.splitlines() if l.strip()]:
        who, _, body = line.partition(":")
        body = highlight_masks(esc(body.strip() or line))
        if is_handoff(line):
            parts.append(f"<div class='msg handoff'><div class='who'>🤖 BOT → 👤 OPERATOR</div>{body}</div>")
        elif who.strip().lower() == "bot":
            parts.append(f"<div class='msg bot'><div class='who'>🤖 BOT</div>{body}</div>")
        else:
            parts.append(f"<div class='msg cust'><div class='who'>MÜŞTƏRİ</div>{body}</div>")
    st.markdown("<div class='chat'>" + "".join(parts) + "</div>", unsafe_allow_html=True)


def render_profile(p: dict) -> None:
    st.markdown(
        f"<div class='profile'><div class='muted'>Müştəri profili (CRM · uydurma məlumat)</div>"
        f"<div class='name'>👤 {esc(p['name'])}</div>"
        f"<div class='row'>🗓 {p['tenure_years']} ildir müştəridir · 📱 {esc(p['tariff'])} ({p['monthly_azn']} AZN/ay)</div>"
        f"<div class='row'>📞 Son 30 gündə {p['contacts_30d']} müraciət · ⏳ Növbədə {p['waiting_min']} dəq</div></div>",
        unsafe_allow_html=True,
    )


def render_insights(result, profile: dict | None, key: str) -> None:
    """Everything the agent needs after the handoff, for one analyzed chat."""
    a = result.analysis
    color = RISK_COLORS[a.churn_risk]

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
    hidden = describe(result.masked)
    privacy = f"🔒 Gizlədildi: {hidden}" if hidden else "🔒 Şəxsi məlumat tapılmadı"
    st.markdown(
        f"<div class='reason'><b>Səbəb:</b> {esc(a.risk_reason)}</div>"
        f"{source_badge(result)}"
        f"<span class='pill privacy'>{privacy}</span>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-title'>📝 Xülasə</div>", unsafe_allow_html=True)
    lines = [l.strip() for l in a.summary.strip().splitlines() if l.strip()]
    st.markdown("<ul class='summary'>" + "".join(f"<li>{esc(l)}</li>" for l in lines) + "</ul>",
                unsafe_allow_html=True)

    st.markdown("<div class='section-title'>🤖 Bot niyə operatora ötürdü?</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='box fail'><b class='t'>{BOT_FAILURE_ICON[a.bot_failure]} {BOT_FAILURE[a.bot_failure]}</b>"
        f"{esc(a.bot_failure_reason)}<div class='muted' style='margin-top:6px'>🔧 {BOT_FAILURE_FIX[a.bot_failure]}</div></div>"
        f"<div class='box faq'><b class='t'>📚 Bot üçün yeni bilik bazası cavabı</b>"
        f"<b>S:</b> {esc(a.faq_question)}<br><b>C:</b> {esc(a.faq_answer)}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-title'>➡️ Növbəti addım</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='action'><span style='font-size:1.4rem'>{ACTION_ICON[a.next_action]}</span>"
        f"{ACTION[a.next_action]}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-title'>🎁 Müştərini saxlamaq üçün təklif</div>", unsafe_allow_html=True)
    offer = suggest(a.category, a.churn_risk, profile)
    if offer:
        value = f" · müştərinin illik dəyəri ~{offer.customer_value_azn:.0f} AZN" if offer.customer_value_azn else ""
        items = "".join(f"<li>{esc(i)}</li>" for i in offer.items)
        st.markdown(
            f"<div class='box offer'><b class='t'>{offer.title}</b><ul style='margin:0 0 6px 18px'>{items}</ul>"
            f"<div class='muted'>Təxmini xərc ~{offer.cost_azn:.0f} AZN{value}. {esc(offer.why)}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div class='box nooffer'>Risk aşağıdır, xüsusi təklif tələb olunmur.</div>",
                    unsafe_allow_html=True)

    st.markdown("<div class='section-title'>✉️ Təklif olunan cavab</div>", unsafe_allow_html=True)
    reply = st.text_area("Göndərməzdən əvvəl redaktə edin", value=a.suggested_reply_az, height=130,
                         key=f"reply_{key}_{id(result)}")
    st.code(reply, language=None, wrap_lines=True)
    st.caption("Cavabı kopyalamaq üçün yuxarıdakı qutunun küncündəki ikona basın.")


def priority(result, profile: dict) -> int:
    a = result.analysis
    return RISK_WEIGHT[a.churn_risk] + a.sentiment * 10 + min(profile["waiting_min"], 60)


def run_queue(tickets: list[dict], offline: bool) -> None:
    results, fallbacks = {}, 0
    bar = st.progress(0.0, text="Növbə təhlil edilir...")
    for i, t in enumerate(tickets, start=1):
        names = [t["customer"]["name"]]
        try:
            res = analyze(t["chat"], force_offline=offline, known_names=names, use_cache=True)
        except Exception:  # keep the queue usable if one call fails (quota, network)
            res = analyze(t["chat"], force_offline=True, known_names=names)
            fallbacks += 1
        results[t["id"]] = res
        bar.progress(i / len(tickets), text=f"{i}/{len(tickets)} söhbət təhlil edildi")
    bar.empty()
    st.session_state.queue = results
    if fallbacks:
        st.warning(f"{fallbacks} söhbət üçün süni intellekt cavab vermədi, oflayn qaydalar istifadə olundu.")


def bar_chart(df: pd.DataFrame, label: str, value: str, colors: dict[str, str] | None = None,
              order: list[str] | None = None) -> alt.LayerChart:
    sort = order or "-x"
    base = alt.Chart(df).encode(
        y=alt.Y(f"{label}:N", sort=sort, title=None,
                axis=alt.Axis(labelLimit=240, labelColor="#374151", labelFontSize=12, domain=False, ticks=False)),
        x=alt.X(f"{value}:Q", title=None,
                axis=alt.Axis(grid=True, gridColor="#efecf8", labelColor="#6b7280", tickMinStep=1, domain=False)),
        tooltip=[alt.Tooltip(f"{label}:N", title="Qrup"), alt.Tooltip(f"{value}:Q", title="Söhbət")],
    )
    if colors:
        bars = base.mark_bar(cornerRadiusEnd=4, size=20).encode(
            color=alt.Color(f"{label}:N", scale=alt.Scale(domain=list(colors), range=list(colors.values())),
                            legend=None))
    else:
        bars = base.mark_bar(cornerRadiusEnd=4, size=20, color=BRAND)
    labels = base.mark_text(align="left", dx=5, color="#374151", fontWeight="bold").encode(text=f"{value}:Q")
    return (bars + labels).properties(height=max(110, 36 * len(df))).configure_view(stroke=None)
