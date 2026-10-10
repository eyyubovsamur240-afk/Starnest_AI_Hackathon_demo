"""Priority queue: every escalated chat sorted by churn risk, with the full analysis
(why the bot failed, FAQ entry, next action, retention offer) for the selected row."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from copilot_ui import (
    RISK_COLORS,
    RISK_DOT,
    SENTIMENT_EMOJI,
    card,
    ensure_queue,
    esc,
    load_tickets,
    mode_label,
    priority,
    render_chat,
    render_insights,
    render_profile,
    run_queue,
    setup_page,
)
from i18n import labels, lang, t
from offers import suggest

offline = setup_page(f"📥 {t('page_queue')}")
L = labels()
tickets = load_tickets()
by_id = {t["id"]: t for t in tickets}
ensure_queue(tickets, offline)

ctrl1, ctrl2 = st.columns([3, 1], vertical_alignment="bottom")
with ctrl1:
    count = st.slider(t("queue_size"), 5, len(tickets), len(tickets) if offline else 15, help=t("queue_size_help"))
with ctrl2:
    if st.button(t("queue_btn"), type="primary", width="stretch"):
        run_queue(tickets[:count], offline)

queue = st.session_state.get("queue")
if not queue:
    st.markdown(
        "<div class='empty'><div style='font-size:2.2rem'>📥</div>"
        f"<div style='font-weight:600;margin:6px 0'>{t('queue_empty_title')}</div>{t('queue_empty')}</div>",
        unsafe_allow_html=True,
    )
else:
    ranked = sorted(queue.items(), key=lambda kv: priority(kv[1], by_id[kv[0]]["customer"]), reverse=True)
    rows = []
    for rank, (tid, res) in enumerate(ranked, start=1):
        a, p = res.analysis, by_id[tid]["customer"]
        rows.append({
            "#": rank,
            "ID": tid,
            t("customer"): p["name"],
            t("col_risk"): f"{RISK_DOT[a.churn_risk]} {L.RISK[a.churn_risk]}",
            t("mood"): f"{SENTIMENT_EMOJI[a.sentiment]} {a.sentiment}/5",
            t("category"): L.CATEGORY[a.category],
            t("col_why"): f"{L.BOT_FAILURE_ICON[a.bot_failure]} {L.BOT_FAILURE[a.bot_failure]}",
            t("col_waiting"): t("minutes", m=p["waiting_min"]),
            t("col_offer"): "🎁" if suggest(a.category, a.churn_risk, p, lang()) else "",
            t("col_who"): mode_label(res.mode),
        })
    high = sum(1 for _, r in ranked if r.analysis.churn_risk == "high")
    k1, k2, k3 = st.columns(3)
    k1.markdown(card(t("in_queue"), t("n_chats", n=len(ranked))), unsafe_allow_html=True)
    k2.markdown(card(t("high_risk"), f"<span style='color:{RISK_COLORS['high']}'>{high}</span>",
                     t("answer_first")), unsafe_allow_html=True)
    top = rows[0]
    k3.markdown(card(t("next_customer"), esc(top[t("customer")]), f"{top[t('col_risk')]} · {top[t('col_waiting')]}"),
                unsafe_allow_html=True)
    st.caption(t("queue_order"))
    event = st.dataframe(
        pd.DataFrame(rows), hide_index=True, width="stretch", height=min(38 * len(rows) + 40, 420),
        on_select="rerun", selection_mode="single-row", key="queue_table",
        column_config={"#": st.column_config.NumberColumn(width="small"),
                       t("col_offer"): st.column_config.TextColumn(width="small")},
    )
    picked = event.selection.rows[0] if event.selection.rows else 0
    tid = rows[picked]["ID"]
    ticket, res = by_id[tid], queue[tid]

    st.markdown(f"<div class='section-title'>📂 {tid} · {esc(ticket['customer']['name'])}</div>",
                unsafe_allow_html=True)
    left, right = st.columns([5, 6], gap="large")
    with left:
        render_profile(ticket["customer"])
        show_masked = st.toggle(t("show_masked"), key=f"mask_{tid}")
        render_chat(res.masked_chat if show_masked else ticket["chat"])
    with right:
        render_insights(res, ticket["customer"], key=tid)
