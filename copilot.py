"""Core logic: turn an escalated chat into a structured analysis.

Uses Gemini with structured JSON output when GEMINI_API_KEY is set, and a simple
keyword-based fallback otherwise so the UI and eval still run offline.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Literal

from pydantic import BaseModel, Field

from prompts import FEW_SHOT, SYSTEM_PROMPT

MODEL = os.getenv("COPILOT_MODEL", "gemini-2.5-flash")


class Analysis(BaseModel):
    summary: str = Field(description="Exactly 3 short lines separated by newlines")
    category: Literal[
        "billing", "roaming", "tariff", "internet_speed",
        "network_coverage", "sim_card", "refund", "other",
    ]
    sentiment: int = Field(ge=1, le=5)
    churn_risk: Literal["low", "medium", "high"]
    risk_reason: str
    suggested_reply_az: str
    next_action: Literal[
        "refund", "tariff_change", "escalate_to_tech", "unblock_sim",
        "explain_charges", "retention_offer", "no_action",
    ]


class AnalysisResult(BaseModel):
    analysis: Analysis
    seconds: float
    mode: Literal["llm", "offline"]


def llm_available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def _build_contents(chat: str) -> list[dict]:
    contents: list[dict] = []
    for ex in FEW_SHOT:
        contents.append({"role": "user", "parts": [{"text": f"Escalated chat:\n\n{ex['chat']}"}]})
        contents.append({"role": "model", "parts": [{"text": json.dumps(ex["output"], ensure_ascii=False)}]})
    contents.append({"role": "user", "parts": [{"text": f"Escalated chat:\n\n{chat}"}]})
    return contents


def analyze_llm(chat: str) -> Analysis:
    from google import genai
    from google.genai import types

    client = genai.Client()  # reads GEMINI_API_KEY (or GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=_build_contents(chat),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Analysis,
            temperature=0.2,
        ),
    )
    if isinstance(response.parsed, Analysis):
        return response.parsed
    if response.text:
        return Analysis.model_validate_json(response.text)
    raise RuntimeError("Model returned no analysis (empty or blocked response)")


# --- Offline fallback -------------------------------------------------------
# Keyword rules in AZ / RU / EN. Good enough to demo the UI without network;
# the LLM path is what the eval numbers should be reported on.

_CATEGORY_KEYWORDS = {
    "roaming": ["roaming", "rouminq", "роуминг", "xaricdə", "за границ", "abroad"],
    "sim_card": ["sim", "сим", "puk", "esim", "bloklan", "заблокир"],
    "refund": ["qaytar", "верните", "возврат", "refund", "money back"],
    "internet_speed": ["internet", "интернет", "4g", "5g", "speed", "sürət", "yavaş", "медлен", "mb/s"],
    "network_coverage": ["siqnal", "сигнал", "signal", "zəng kəsilir", "связь", "no service", "şəbəkə yoxdur"],
    "tariff": ["tarif", "тариф", "paket", "пакет", "plan", "bonus", "gb"],
    "billing": ["balans", "баланс", "azn", "manat", "манат", "çıxılıb", "списал", "charge", "hesab", "счет"],
}

_CHURN_KEYWORDS = [
    "bakcell", "nar", "keçəcəm", "kececem", "keçirəm", "başqa operator", "перейду", "уйду",
    "другому оператору", "расторга", "switch operator", "moving to", "leave you", "nömrəni ləğv",
    "şikayət", "жалоб", "министерств", "regulator", "instagram", "facebook", "axırıncı dəfə", "son dəfə",
]

# Signs of frustration short of a churn threat: repeated contact, waiting, lost money.
_FRUSTRATION_KEYWORDS = [
    "niyə", "nə vaxt", "почему", "когда", "why", "again", "dünən", "yenə", "уже", "жду", "waiting",
    "qaytarın", "верните", "back", "promised", "günahım", "kim izah", "кому", "check your",
]

_ANGER_KEYWORDS = ["!!", "bezdim", "rezalət", "надоело", "ужас", "позор", "worst", "ridiculous", "biabır", "кошмар"]

_REPLIES = {
    "billing": "Salam! Narahatçılığa görə üzr istəyirik. Balansınızdan edilən çıxılmaları yoxlayıram və sizə ətraflı izah verəcəyəm. Səhv tutulma aşkar olunarsa, məbləğ geri qaytarılacaq.",
    "roaming": "Salam! Yaşadığınız çətinliyə görə üzr istəyirik. Rouminq xidmətinizin vəziyyətini və tutulmaları yoxlayıram, qısa zamanda sizə dəqiq məlumat verəcəyəm.",
    "tariff": "Salam! Müraciətiniz üçün təşəkkür edirik. Tarifinizin şərtlərini yoxlayıram və sizə ən uyğun variantı təklif edəcəyəm.",
    "internet_speed": "Salam! İnternetlə bağlı problemə görə üzr istəyirik. Müraciətinizi texniki şöbəyə ötürürəm ki, ərazinizdəki şəbəkəni yoxlasınlar. Nəticə barədə sizə məlumat veriləcək.",
    "network_coverage": "Salam! Şəbəkə ilə bağlı narahatçılığa görə üzr istəyirik. Ünvanınız üzrə siqnal problemini texniki şöbəyə ötürürəm, onlar sizinlə əlaqə saxlayacaq.",
    "sim_card": "Salam! SIM kartınızla bağlı problemi yoxlayıram. Şəxsiyyətinizi təsdiqlədikdən sonra kartınızı aktivləşdirə bilərik.",
    "refund": "Salam! Narahatçılığa görə üzr istəyirik. Tutulan məbləğin geri qaytarılması üçün müraciət açıram və nəticə barədə sizə SMS ilə məlumat veriləcək.",
    "other": "Salam! Müraciətiniz üçün təşəkkür edirik. Məsələni yoxlayıram və qısa zamanda sizə cavab verəcəyəm.",
}

_ACTIONS = {
    "billing": "explain_charges",
    "roaming": "explain_charges",
    "tariff": "tariff_change",
    "internet_speed": "escalate_to_tech",
    "network_coverage": "escalate_to_tech",
    "sim_card": "unblock_sim",
    "refund": "refund",
    "other": "no_action",
}


def analyze_offline(chat: str) -> Analysis:
    text = chat.lower()
    scores = {cat: sum(text.count(k) for k in kws) for cat, kws in _CATEGORY_KEYWORDS.items()}
    category = max(scores, key=scores.get) if max(scores.values()) > 0 else "other"

    churn_hits = [k for k in _CHURN_KEYWORDS if re.search(rf"\b{re.escape(k)}", text)]
    anger = sum(text.count(k) for k in _ANGER_KEYWORDS) + text.count("!") // 3
    frustration = min(2, sum(1 for k in _FRUSTRATION_KEYWORDS if k in text))
    sentiment = max(1, min(5, 1 + frustration + anger + (2 if churn_hits else 0)))
    if churn_hits:
        risk, reason = "high", f"Customer mentions: {', '.join(churn_hits[:3])}."
    elif sentiment >= 3:
        risk, reason = "medium", "Customer is clearly frustrated but has not threatened to leave."
    else:
        risk, reason = "low", "Calm tone and no mention of leaving."

    customer_lines = [l.split(":", 1)[-1].strip() for l in chat.splitlines() if l.lower().startswith(("customer", "müştəri", "клиент"))]
    first = customer_lines[0] if customer_lines else chat.strip().splitlines()[0]
    last = customer_lines[-1] if customer_lines else first
    summary = "\n".join([
        f"Issue ({category.replace('_', ' ')}): {first[:110]}",
        f"Chat has {len(chat.splitlines())} messages; the bot did not resolve it.",
        f"Latest from customer: {last[:110]}",
    ])
    action = "retention_offer" if risk == "high" and _ACTIONS[category] == "no_action" else _ACTIONS[category]
    return Analysis(
        summary=summary,
        category=category,
        sentiment=sentiment,
        churn_risk=risk,
        risk_reason=reason,
        suggested_reply_az=_REPLIES[category],
        next_action=action,
    )


def analyze(chat: str, force_offline: bool = False) -> AnalysisResult:
    """Analyze one chat. Falls back to offline rules if no API key is configured."""
    start = time.perf_counter()
    if llm_available() and not force_offline:
        analysis, mode = analyze_llm(chat), "llm"
    else:
        analysis, mode = analyze_offline(chat), "offline"
    return AnalysisResult(analysis=analysis, seconds=round(time.perf_counter() - start, 2), mode=mode)


if __name__ == "__main__":
    import sys

    chat_text = sys.stdin.read() if not sys.stdin.isatty() else FEW_SHOT[1]["chat"]
    print(analyze(chat_text).model_dump_json(indent=2))
