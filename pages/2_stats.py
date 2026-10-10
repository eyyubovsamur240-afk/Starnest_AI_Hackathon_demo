"""Statistics across the analyzed queue: categories, why the bot handed over, churn-risk
mix, masked personal data, and new FAQ entries for the bot."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from copilot_ui import RISK_COLORS, ai_text_note, bar_chart, card, ensure_queue, load_tickets, setup_page
from i18n import labels, t

offline = setup_page(f"📈 {t('page_stats')}")
L = labels()
CHATS = t("chats_col")
tickets = load_tickets()
by_id = {t["id"]: t for t in tickets}
ensure_queue(tickets, offline)

queue = st.session_state.get("queue")
if not queue:
    st.info(t("stats_empty"))
else:
    analyses = {tid: r.analysis for tid, r in queue.items()}
    n = len(analyses)
    high = sum(1 for a in analyses.values() if a.churn_risk == "high")
    avg_sent = sum(a.sentiment for a in analyses.values()) / n
    avg_wait = sum(by_id[t]["customer"]["waiting_min"] for t in analyses) / n
    fails = pd.Series([L.BOT_FAILURE[a.bot_failure] for a in analyses.values()]).value_counts()
    masked_chats = sum(1 for r in queue.values() if r.masked)
    by_gemini = sum(1 for r in queue.values() if r.mode != "offline")
    st.caption(t("decided_split", g=by_gemini, o=n - by_gemini))

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(card(t("handed_over"), str(n)), unsafe_allow_html=True)
    k2.markdown(card(t("high_risk"), f"<span style='color:{RISK_COLORS['high']}'>{high}</span>",
                     t("may_leave", p=100 * high / n)), unsafe_allow_html=True)
    k3.markdown(card(t("avg_mood"), f"{avg_sent:.1f}/5", t("avg_wait", m=avg_wait)),
                unsafe_allow_html=True)
    k4.markdown(card(t("main_bot_problem"), fails.index[0], t("in_n_chats", n=fails.iloc[0])),
                unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(f"<div class='section-title'>{t('complaint_categories')}</div>", unsafe_allow_html=True)
        cats = pd.Series([L.CATEGORY[a.category] for a in analyses.values()]).value_counts()
        st.altair_chart(bar_chart(cats.rename_axis(t("category")).reset_index(name=CHATS),
                                  t("category"), CHATS), width="stretch")
    with c2:
        st.markdown(f"<div class='section-title'>{t('why_handover_short')}</div>", unsafe_allow_html=True)
        st.altair_chart(bar_chart(fails.rename_axis(t("reason")).reset_index(name=CHATS), t("reason"), CHATS),
                        width="stretch")

    c3, c4 = st.columns(2, gap="large")
    with c3:
        st.markdown(f"<div class='section-title'>{t('churn_risk')}</div>", unsafe_allow_html=True)
        order = ["high", "medium", "low"]
        risk_col = t("col_risk")
        risk_df = pd.DataFrame({
            risk_col: [L.RISK[r] for r in order],
            CHATS: [sum(1 for a in analyses.values() if a.churn_risk == r) for r in order],
        })
        st.altair_chart(bar_chart(risk_df, risk_col, CHATS,
                                  colors={L.RISK[r]: RISK_COLORS[r] for r in order},
                                  order=[L.RISK[r] for r in order]), width="stretch")
    with c4:
        st.markdown(f"<div class='section-title'>{t('privacy')}</div>", unsafe_allow_html=True)
        st.markdown(
            card(t("masked_chats"), f"🔒 {masked_chats} / {n}", t("masked_chats_sub")),
            unsafe_allow_html=True,
        )

    st.markdown(f"<div class='section-title'>{t('faq_title')}</div>", unsafe_allow_html=True)
    st.caption(t("faq_caption"))
    faq = pd.DataFrame([
        {"ID": tid, t("reason"): L.BOT_FAILURE[a.bot_failure], t("category"): L.CATEGORY[a.category],
         t("question"): a.faq_question, t("answer"): a.faq_answer}
        for tid, a in analyses.items() if a.bot_failure != "no_permission"
    ])
    if faq.empty:
        st.write(t("no_faq"))
    else:
        ai_text_note()
        st.dataframe(faq, hide_index=True, width="stretch")
        st.download_button(t("faq_download"), faq.to_csv(index=False).encode("utf-8-sig"),
                           file_name=t("faq_file"), mime="text/csv")
