"""Azerbaijani display labels for the UI. Internal codes stay in English so eval and labels don't change."""

CATEGORY = {
    "billing": "Hesab və ödənişlər",
    "roaming": "Rouminq",
    "tariff": "Tarif və paketlər",
    "internet_speed": "İnternet sürəti",
    "network_coverage": "Şəbəkə əhatəsi",
    "sim_card": "SIM kart",
    "refund": "Pulun qaytarılması",
    "other": "Digər",
}

ACTION = {
    "refund": "Pulu geri qaytarmaq",
    "tariff_change": "Tarifi dəyişmək",
    "escalate_to_tech": "Texniki şöbəyə ötürmək",
    "unblock_sim": "SIM kartı blokdan çıxarmaq",
    "explain_charges": "Tutulmaları izah etmək",
    "retention_offer": "Müştərini saxlamaq üçün təklif vermək",
    "no_action": "Əlavə addım lazım deyil",
}

ACTION_ICON = {
    "refund": "💸", "tariff_change": "🔁", "escalate_to_tech": "🛠️", "unblock_sim": "🔓",
    "explain_charges": "🧾", "retention_offer": "🎁", "no_action": "✅",
}

RISK = {"low": "AŞAĞI", "medium": "ORTA", "high": "YÜKSƏK"}

SENTIMENT = {1: "sakit", 2: "bir az narazı", 3: "narazı", 4: "əsəbi", 5: "çox qəzəbli"}

TONE = {"calm": "sakit", "annoyed": "narazı", "furious": "qəzəbli"}

LANGUAGE = {"az": "AZ", "ru": "RU", "en": "EN", "mixed": "qarışıq"}

BOT_FAILURE = {
    "not_understood": "Bot sualı başa düşmədi",
    "loop": "Bot eyni cavabı təkrarladı",
    "wrong_answer": "Bot yanlış cavab verdi",
    "missing_knowledge": "Botda lazımi məlumat yox idi",
    "no_permission": "Botun səlahiyyəti çatmır",
}

BOT_FAILURE_ICON = {
    "not_understood": "❓", "loop": "🔁", "wrong_answer": "❌", "missing_knowledge": "📚", "no_permission": "🔒",
}

# What the team should change so the bot handles this case next time.
BOT_FAILURE_FIX = {
    "not_understood": "Botun dil modelinə bu ifadələri əlavə edin (AZ/RU/EN, səhv yazılışlar daxil).",
    "loop": "Eyni cavab iki dəfə veriləndən sonra bot dərhal operatora ötürməlidir.",
    "wrong_answer": "Bu ssenari üzrə botun cavab qaydasını yoxlayın və düzəldin.",
    "missing_knowledge": "Aşağıdakı sual-cavabı botun bilik bazasına əlavə edin.",
    "no_permission": "Bu əməliyyat üçün bota sistem inteqrasiyası lazımdır və ya birbaşa operatora ötürülməlidir.",
}
