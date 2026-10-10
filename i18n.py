"""Azerbaijani / English UI text. The language lives in st.session_state["lang"] ("az" by default),
so it carries over between pages. AI-written text (summary, reasons, FAQ, the reply) stays as Gemini
wrote it, in Azerbaijani: translating it would cost extra Gemini requests and the saved answers."""

from __future__ import annotations

import streamlit as st

import labels_az
import labels_en

LANGS = {"az": "🇦🇿 AZ", "en": "🇬🇧 EN"}

TEXT = {
    # app-wide
    "app_name": ("Eskalasiya Köməkçisi", "Escalation Copilot"),
    "language": ("Dil", "Language"),
    "customer": ("Müştəri", "Customer"),
    "page_analysis": ("Söhbət təhlili", "Chat analysis"),
    "page_queue": ("Prioritet növbəsi", "Priority queue"),
    "page_stats": ("Statistika", "Statistics"),
    "demo_data": ("Demo yalnız uydurma söhbətlərdən istifadə edir.", "The demo uses made-up chats only."),
    "demo_data_profiles": ("Demo yalnız uydurma söhbət və profillərdən istifadə edir.",
                           "The demo uses made-up chats and profiles only."),
    "privacy_note": ("🔒 Telefon, ad, kart, e-poçt və FİN kod süni intellektə göndərilməzdən əvvəl gizlədilir.",
                     "🔒 Phone numbers, names, cards, e-mails and FIN codes are masked before anything is sent to the AI."),
    "ai_text_az": ("", "ℹ️ The summary, reasons, FAQ entry and reply are written by the AI in Azerbaijani, "
                       "the language the agent answers the customer in."),
    # sidebar: Gemini status
    "live_mode": ("Canlı rejim: {models}", "Live mode: {models}"),
    "offline_mode": ("Oflayn rejim", "Offline mode"),
    "offline_help": ("Süni intellekt əvəzinə açar söz qaydaları", "Keyword rules instead of the AI"),
    "no_key": ("API açarı yoxdur: yeni söhbətlər ⚙️ oflayn qaydalarla təhlil olunur. "
               "Canlı təhlil üçün GEMINI_API_KEY təyin edin.",
               "No API key: new chats are analysed with the ⚙️ offline rules. "
               "Set GEMINI_API_KEY for live analysis."),
    "saved_answers": ("💾 Yaddaşda {n} hazır Gemini cavabı var: bu söhbətlər limit xərcləmədən açılır.",
                      "💾 {n} saved Gemini answers: these chats open without using any quota."),
    "quota_hours": (" Limit təxminən {h} saatdan sonra yenilənir.", " The limit resets in about {h} h."),
    "quota_out": ("⏳ Gemini-nin gündəlik pulsuz sorğu limiti bitib.{hours}"
                  " Yadda saxlanmış Gemini cavabları göstərilir, qalanları ⚙️ oflayn qaydalarla təhlil olunur.",
                  "⏳ Gemini's free daily request limit is used up.{hours}"
                  " Saved Gemini answers are shown; the rest are analysed with the ⚙️ offline rules."),
    "gemini_broken": ("⚠️ Gemini işləmir (model və ya API açarı problemi), ⚙️ oflayn qaydalar istifadə olunur.\n\n{exc}",
                      "⚠️ Gemini isn't working (a model or API key problem), so the ⚙️ offline rules are used.\n\n{exc}"),
    # who decided
    "mode_llm": ("🤖 Gemini", "🤖 Gemini"),
    "mode_cache": ("🤖 Gemini · yaddaşdan", "🤖 Gemini · saved"),
    "mode_offline": ("⚙️ Oflayn qaydalar", "⚙️ Offline rules"),
    "badge_offline": ("⚙️ Oflayn açar söz qaydaları · Gemini istifadə olunmayıb",
                      "⚙️ Offline keyword rules · Gemini not used"),
    "badge_saved": ("yaddaşdan", "saved answer"),
    "badge_seconds": ("{s:.1f} san", "{s:.1f} s"),
    "badge_gemini": ("🤖 Gemini ({model}) qərar verdi · {when}", "🤖 Gemini ({model}) decided · {when}"),
    # main screen
    "tagline": ("Botun həll edə bilmədiyi söhbət, bir baxışda.", "The chat the bot couldn't solve, at a glance."),
    "paste_own": ("(öz söhbətinizi yapışdırın)", "(paste your own chat)"),
    "customer_chat": ("💬 Müştəri söhbəti", "💬 Customer chat"),
    "chat": ("Söhbət", "Chat"),
    "paste_placeholder": ("Bot ilə müştərinin yazışmasını bura yapışdırın...\nMüştəri: ...\nBot: ...",
                          "Paste the bot ↔ customer chat here...\nCustomer: ...\nBot: ..."),
    "analysis": ("🔍 Təhlil", "🔍 Analysis"),
    "analyze_btn": ("Təhlil et", "Analyse"),
    "reading": ("Söhbət oxunur...", "Reading the chat..."),
    "analysis_failed": ("Təhlil alınmadı: {exc}. Yan paneldə \"Oflayn rejim\"i yoxlayın.",
                        "Analysis failed: {exc}. Try \"Offline mode\" in the sidebar."),
    "pick_chat": ("Söhbəti seçin və <b>Təhlil et</b> düyməsini basın.", "Pick a chat and press <b>Analyse</b>."),
    "summary": ("Xülasə", "Summary"),
    "mood": ("Əhval", "Mood"),
    "churn_risk": ("Müştərini itirmə riski", "Churn risk"),
    "issue_category": ("Problem kateqoriyası", "Issue category"),
    "category": ("Kateqoriya", "Category"),
    "suggested_reply": ("Təklif olunan cavab", "Suggested reply"),
    "summary_ok": ("Xülasə dəqiqdir?", "Is the summary accurate?"),
    "reply_quality": ("Cavabın keyfiyyəti", "Reply quality"),
    "ai_accuracy": ("📊 AI dəqiqliyi", "📊 AI accuracy"),
    "human_rating": ("İnsan qiymətləndirməsi", "Human rating"),
    "summaries_checked": ("{n} xülasə yoxlanılıb", "{n} summaries checked"),
    "rate_thumbs": ("Təhlildən sonra 👍/👎 ilə qiymətləndirin", "Rate with 👍/👎 after an analysis"),
    "within_1": ("±1 bal fərqlə düzgün", "Correct within ±1 point"),
    "reply_quality_metric": ("Cavab keyfiyyəti", "Reply quality"),
    "replies_rated": ("{n} cavab qiymətləndirilib", "{n} replies rated"),
    "rate_stars": ("Təhlildən sonra ulduzla qiymətləndirin", "Rate with stars after an analysis"),
    "eval_partial": (" (qismən: {total} söhbətdən {n})", " (partial: {n} of {total} chats)"),
    "eval_llm": ("Kateqoriya və əhval: Gemini, {n} uydurma söhbət üzrə eval.py nəticəsi{part}.",
                 "Category and mood: Gemini, eval.py result on {n} made-up chats{part}."),
    "eval_offline": ("Kateqoriya və əhval: {n} uydurma söhbət üzrə **oflayn açar söz qaydalarının** nəticəsi, "
                     "Gemini-nin yox. Gemini-ni yoxlamaq üçün açarla `python eval.py` işə salın.",
                     "Category and mood: result of the **offline keyword rules** on {n} made-up chats, "
                     "not Gemini. Run `python eval.py` with a key to test Gemini."),
    "eval_none": ("Kateqoriya və əhval üçün əvvəlcə `python eval.py` işə salın.",
                  "Run `python eval.py` first to see category and mood accuracy."),
    # analysis panel (queue page)
    "crm_profile": ("Müştəri profili (CRM · uydurma məlumat)", "Customer profile (CRM · made-up data)"),
    "profile_tenure": ("🗓 {years} ildir müştəridir · 📱 {tariff} ({azn} AZN/ay)",
                       "🗓 Customer for {years} years · 📱 {tariff} ({azn} AZN/month)"),
    "profile_contacts": ("📞 Son 30 gündə {n} müraciət · ⏳ Növbədə {m} dəq",
                         "📞 {n} contacts in the last 30 days · ⏳ Waiting {m} min"),
    "masked": ("🔒 Gizlədildi: {what}", "🔒 Masked: {what}"),
    "no_personal": ("🔒 Şəxsi məlumat tapılmadı", "🔒 No personal data found"),
    "reason": ("Səbəb", "Reason"),
    "why_handover": ("🤖 Bot niyə operatora ötürdü?", "🤖 Why did the bot hand over?"),
    "new_faq": ("📚 Bot üçün yeni bilik bazası cavabı", "📚 New knowledge-base entry for the bot"),
    "faq_q": ("S", "Q"),
    "faq_a": ("C", "A"),
    "next_step": ("➡️ Növbəti addım", "➡️ Next step"),
    "retention": ("🎁 Müştərini saxlamaq üçün təklif", "🎁 Offer to keep the customer"),
    "offer_value": (" · müştərinin illik dəyəri ~{v:.0f} AZN", " · customer's yearly value ~{v:.0f} AZN"),
    "offer_cost": ("Təxmini xərc ~{c:.0f} AZN{value}. {why}", "Estimated cost ~{c:.0f} AZN{value}. {why}"),
    "no_offer": ("Risk aşağıdır, xüsusi təklif tələb olunmur.", "Risk is low, no special offer needed."),
    "reply_section": ("✉️ Təklif olunan cavab", "✉️ Suggested reply"),
    "edit_before_send": ("Göndərməzdən əvvəl redaktə edin", "Edit before sending"),
    "copy_hint": ("Cavabı kopyalamaq üçün yuxarıdakı qutunun küncündəki ikona basın.",
                  "To copy the reply, click the icon in the corner of the box above."),
    "queue_running": ("Növbə təhlil edilir...", "Analysing the queue..."),
    "queue_progress": ("{i}/{n} söhbət təhlil edildi", "{i}/{n} chats analysed"),
    "queue_fallbacks": ("{n} söhbət üçün süni intellekt cavab vermədi, oflayn qaydalar istifadə olundu.",
                        "The AI didn't answer for {n} chats, so the offline rules were used."),
    "tooltip_group": ("Qrup", "Group"),
    # queue page
    "queue_size": ("Növbədəki söhbət sayı", "Chats in the queue"),
    "queue_size_help": ("Pulsuz Gemini planında gündə 20 sorğu limiti var. Yadda saxlanmış cavabı olan söhbətlər "
                        "limit xərcləmir, yalnız yeni söhbətlər Gemini-yə göndərilir.",
                        "The free Gemini plan allows 20 requests a day. Chats with a saved answer use no quota; "
                        "only new chats are sent to Gemini."),
    "queue_btn": ("▶ Növbəni təhlil et", "▶ Analyse the queue"),
    "queue_empty_title": ("Növbə hələ təhlil edilməyib", "The queue hasn't been analysed yet"),
    "queue_empty": ("Söhbət sayını seçin və <b>Növbəni təhlil et</b> düyməsini basın.",
                    "Choose how many chats and press <b>Analyse the queue</b>."),
    "col_risk": ("Risk", "Risk"),
    "col_why": ("Bot niyə ötürdü", "Why the bot handed over"),
    "col_waiting": ("Gözləyir", "Waiting"),
    "minutes": ("{m} dəq", "{m} min"),
    "col_offer": ("Təklif", "Offer"),
    "col_who": ("Kim qərar verdi", "Decided by"),
    "in_queue": ("Növbədə", "In the queue"),
    "n_chats": ("{n} söhbət", "{n} chats"),
    "high_risk": ("Yüksək risk", "High risk"),
    "answer_first": ("birinci bunlara cavab verin", "answer these first"),
    "next_customer": ("Növbəti müştəri", "Next customer"),
    "queue_order": ("Sıralama: əvvəl risk, sonra əhval, sonra gözləmə vaxtı. Ətraflı baxmaq üçün sətrə klikləyin.",
                    "Order: risk first, then mood, then waiting time. Click a row for the details."),
    "show_masked": ("Süni intellektə göndərilən (gizlədilmiş) mətni göstər", "Show the (masked) text sent to the AI"),
    # statistics page
    "stats_empty": ("Statistika növbədəki söhbətlərdən qurulur. Əvvəlcə **Prioritet növbəsi** bölməsində növbəni təhlil edin.",
                    "Statistics are built from the chats in the queue. Analyse the queue on the **Priority queue** page first."),
    "decided_split": ("🤖 Gemini qərar verdi: {g} söhbət · ⚙️ Oflayn qaydalar: {o} söhbət",
                      "🤖 Decided by Gemini: {g} chats · ⚙️ Offline rules: {o} chats"),
    "handed_over": ("Operatora ötürülən söhbət", "Chats handed to an agent"),
    "may_leave": ("{p:.0f}% müştəri itirilə bilər", "{p:.0f}% of customers may leave"),
    "avg_mood": ("Orta əhval", "Average mood"),
    "avg_wait": ("orta gözləmə {m:.0f} dəq", "average wait {m:.0f} min"),
    "main_bot_problem": ("Botun əsas problemi", "The bot's main problem"),
    "in_n_chats": ("{n} söhbətdə", "in {n} chats"),
    "complaint_categories": ("Şikayət kateqoriyaları", "Complaint categories"),
    "why_handover_short": ("Bot niyə operatora ötürdü", "Why the bot handed over"),
    "chats_col": ("Söhbət", "Chats"),
    "privacy": ("Məxfilik", "Privacy"),
    "masked_chats": ("Şəxsi məlumatı gizlədilən söhbət", "Chats with personal data masked"),
    "masked_chats_sub": ("telefon, ad, kart, e-poçt və FİN kod süni intellektə getmədi",
                         "phone numbers, names, cards, e-mails and FIN codes never reached the AI"),
    "faq_title": ("📚 Botun bilik bazasına əlavə ediləcək cavablar", "📚 Answers to add to the bot's knowledge base"),
    "faq_caption": ("Bot məlumat çatışmadığı, sualı başa düşmədiyi və ya səhv cavab verdiyi söhbətlərdən yaranıb.",
                    "Taken from chats where the bot lacked information, didn't understand or answered wrongly."),
    "question": ("Sual", "Question"),
    "answer": ("Cavab", "Answer"),
    "no_faq": ("Bu növbədə bilik bazası üçün yeni sual yoxdur.", "No new knowledge-base questions in this queue."),
    "faq_download": ("⬇️ FAQ siyahısını yüklə (CSV)", "⬇️ Download the FAQ list (CSV)"),
    "faq_file": ("bot_faq_tovsiyeleri.csv", "bot_faq_suggestions.csv"),
}


def lang() -> str:
    return st.session_state.get("lang", "az")


def t(key: str, **kwargs) -> str:
    """The text for `key` in the current language, formatted with kwargs."""
    text = TEXT[key][1 if lang() == "en" else 0]
    return text.format(**kwargs) if kwargs else text


def labels():
    """The label module (CATEGORY, RISK, ...) for the current language."""
    return labels_en if lang() == "en" else labels_az


def language_switch() -> None:
    """AZ / EN switch at the top of the sidebar. Kept in a plain session key so it survives page changes."""
    current = lang()
    choice = st.radio(f"{TEXT['language'][0]} / {TEXT['language'][1]}", list(LANGS), index=list(LANGS).index(current),
                      format_func=LANGS.get, horizontal=True)
    if choice != current:
        st.session_state.lang = choice
        st.rerun()
