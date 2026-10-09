"""Statistics across the analyzed queue: categories, why the bot handed over, churn-risk
mix, masked personal data, and new FAQ entries for the bot."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from labels_az import BOT_FAILURE, CATEGORY, RISK
from ui import RISK_COLORS, bar_chart, card, ensure_queue, load_tickets, setup_page

offline = setup_page("📈 Statistika")
tickets = load_tickets()
by_id = {t["id"]: t for t in tickets}
ensure_queue(tickets, offline)

queue = st.session_state.get("queue")
if not queue:
    st.info("Statistika növbədəki söhbətlərdən qurulur. Əvvəlcə **Prioritet növbəsi** bölməsində növbəni təhlil edin.")
else:
    analyses = {tid: r.analysis for tid, r in queue.items()}
    n = len(analyses)
    high = sum(1 for a in analyses.values() if a.churn_risk == "high")
    avg_sent = sum(a.sentiment for a in analyses.values()) / n
    avg_wait = sum(by_id[t]["customer"]["waiting_min"] for t in analyses) / n
    fails = pd.Series([BOT_FAILURE[a.bot_failure] for a in analyses.values()]).value_counts()
    masked_chats = sum(1 for r in queue.values() if r.masked)
    by_gemini = sum(1 for r in queue.values() if r.mode != "offline")
    st.caption(f"🤖 Gemini qərar verdi: {by_gemini} söhbət · ⚙️ Oflayn qaydalar: {n - by_gemini} söhbət")

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(card("Operatora ötürülən söhbət", str(n)), unsafe_allow_html=True)
    k2.markdown(card("Yüksək risk", f"<span style='color:{RISK_COLORS['high']}'>{high}</span>",
                     f"{100 * high / n:.0f}% müştəri itirilə bilər"), unsafe_allow_html=True)
    k3.markdown(card("Orta əhval", f"{avg_sent:.1f}/5", f"orta gözləmə {avg_wait:.0f} dəq"),
                unsafe_allow_html=True)
    k4.markdown(card("Botun əsas problemi", fails.index[0], f"{fails.iloc[0]} söhbətdə"),
                unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("<div class='section-title'>Şikayət kateqoriyaları</div>", unsafe_allow_html=True)
        cats = pd.Series([CATEGORY[a.category] for a in analyses.values()]).value_counts()
        st.altair_chart(bar_chart(cats.rename_axis("Kateqoriya").reset_index(name="Söhbət"),
                                  "Kateqoriya", "Söhbət"), width="stretch")
    with c2:
        st.markdown("<div class='section-title'>Bot niyə operatora ötürdü</div>", unsafe_allow_html=True)
        st.altair_chart(bar_chart(fails.rename_axis("Səbəb").reset_index(name="Söhbət"), "Səbəb", "Söhbət"),
                        width="stretch")

    c3, c4 = st.columns(2, gap="large")
    with c3:
        st.markdown("<div class='section-title'>Müştərini itirmə riski</div>", unsafe_allow_html=True)
        order = ["high", "medium", "low"]
        risk_df = pd.DataFrame({
            "Risk": [RISK[r] for r in order],
            "Söhbət": [sum(1 for a in analyses.values() if a.churn_risk == r) for r in order],
        })
        st.altair_chart(bar_chart(risk_df, "Risk", "Söhbət",
                                  colors={RISK[r]: RISK_COLORS[r] for r in order},
                                  order=[RISK[r] for r in order]), width="stretch")
    with c4:
        st.markdown("<div class='section-title'>Məxfilik</div>", unsafe_allow_html=True)
        st.markdown(
            card("Şəxsi məlumatı gizlədilən söhbət", f"🔒 {masked_chats} / {n}",
                 "telefon, ad, kart, e-poçt və FİN kod süni intellektə getmədi"),
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-title'>📚 Botun bilik bazasına əlavə ediləcək cavablar</div>",
                unsafe_allow_html=True)
    st.caption("Bot məlumat çatışmadığı, sualı başa düşmədiyi və ya səhv cavab verdiyi söhbətlərdən yaranıb.")
    faq = pd.DataFrame([
        {"ID": tid, "Səbəb": BOT_FAILURE[a.bot_failure], "Kateqoriya": CATEGORY[a.category],
         "Sual": a.faq_question, "Cavab": a.faq_answer}
        for tid, a in analyses.items() if a.bot_failure != "no_permission"
    ])
    if faq.empty:
        st.write("Bu növbədə bilik bazası üçün yeni sual yoxdur.")
    else:
        st.dataframe(faq, hide_index=True, width="stretch")
        st.download_button("⬇️ FAQ siyahısını yüklə (CSV)", faq.to_csv(index=False).encode("utf-8-sig"),
                           file_name="bot_faq_tovsiyeleri.csv", mime="text/csv")
