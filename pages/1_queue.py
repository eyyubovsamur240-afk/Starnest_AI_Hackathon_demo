"""Priority queue: every escalated chat sorted by churn risk, with the full analysis
(why the bot failed, FAQ entry, next action, retention offer) for the selected row."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from copilot_ui import (
    MODE_LABEL,
    RISK_COLORS,
    RISK_DOT,
    SENTIMENT_EMOJI,
    card,
    ensure_queue,
    esc,
    load_tickets,
    priority,
    render_chat,
    render_insights,
    render_profile,
    run_queue,
    setup_page,
)
from labels_az import BOT_FAILURE, BOT_FAILURE_ICON, CATEGORY, RISK
from offers import suggest

offline = setup_page("📥 Prioritet növbəsi")
tickets = load_tickets()
by_id = {t["id"]: t for t in tickets}
ensure_queue(tickets, offline)

ctrl1, ctrl2 = st.columns([3, 1], vertical_alignment="bottom")
with ctrl1:
    count = st.slider("Növbədəki söhbət sayı", 5, len(tickets), len(tickets) if offline else 15,
                      help="Pulsuz Gemini planında sorğu limiti var, 40 söhbət bir neçə dəqiqə çəkə bilər. "
                           "Nəticələr yaddaşda saxlanılır, növbəti dəfə dərhal açılır.")
with ctrl2:
    if st.button("▶ Növbəni təhlil et", type="primary", width="stretch"):
        run_queue(tickets[:count], offline)

queue = st.session_state.get("queue")
if not queue:
    st.markdown(
        "<div class='empty'><div style='font-size:2.2rem'>📥</div>"
        "<div style='font-weight:600;margin:6px 0'>Növbə hələ təhlil edilməyib</div>"
        "Söhbət sayını seçin və <b>Növbəni təhlil et</b> düyməsini basın.</div>",
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
            "Müştəri": p["name"],
            "Risk": f"{RISK_DOT[a.churn_risk]} {RISK[a.churn_risk]}",
            "Əhval": f"{SENTIMENT_EMOJI[a.sentiment]} {a.sentiment}/5",
            "Kateqoriya": CATEGORY[a.category],
            "Bot niyə ötürdü": f"{BOT_FAILURE_ICON[a.bot_failure]} {BOT_FAILURE[a.bot_failure]}",
            "Gözləyir": f"{p['waiting_min']} dəq",
            "Təklif": "🎁" if suggest(a.category, a.churn_risk, p) else "",
        "Kim qərar verdi": MODE_LABEL[res.mode],
        })
    high = sum(1 for _, r in ranked if r.analysis.churn_risk == "high")
    k1, k2, k3 = st.columns(3)
    k1.markdown(card("Növbədə", f"{len(ranked)} söhbət"), unsafe_allow_html=True)
    k2.markdown(card("Yüksək risk", f"<span style='color:{RISK_COLORS['high']}'>{high}</span>",
                     "birinci bunlara cavab verin"), unsafe_allow_html=True)
    k3.markdown(card("Növbəti müştəri", esc(rows[0]["Müştəri"]), f"{rows[0]['Risk']} · {rows[0]['Gözləyir']}"),
                unsafe_allow_html=True)
    st.caption("Sıralama: əvvəl risk, sonra əhval, sonra gözləmə vaxtı. Ətraflı baxmaq üçün sətrə klikləyin.")
    event = st.dataframe(
        pd.DataFrame(rows), hide_index=True, width="stretch", height=min(38 * len(rows) + 40, 420),
        on_select="rerun", selection_mode="single-row", key="queue_table",
        column_config={"#": st.column_config.NumberColumn(width="small"),
                       "Təklif": st.column_config.TextColumn(width="small")},
    )
    picked = event.selection.rows[0] if event.selection.rows else 0
    tid = rows[picked]["ID"]
    ticket, res = by_id[tid], queue[tid]

    st.markdown(f"<div class='section-title'>📂 {tid} · {esc(ticket['customer']['name'])}</div>",
                unsafe_allow_html=True)
    left, right = st.columns([5, 6], gap="large")
    with left:
        render_profile(ticket["customer"])
        show_masked = st.toggle("Süni intellektə göndərilən (gizlədilmiş) mətni göstər", key=f"mask_{tid}")
        render_chat(res.masked_chat if show_masked else ticket["chat"])
    with right:
        render_insights(res, ticket["customer"], key=tid)
