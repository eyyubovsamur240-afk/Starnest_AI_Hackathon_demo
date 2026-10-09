"""Core logic: turn a bot-to-customer chat that was handed over to a human into a structured analysis.

Personal data is masked first (privacy.py), then the chat goes to Gemini with structured JSON output
when GEMINI_API_KEY is set. Without a key, a keyword-based fallback keeps the UI and eval running offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from labels_az import CATEGORY
from privacy import mask
from prompts import FEW_SHOT, SYSTEM_PROMPT

DEFAULT_MODEL = "gemini-3.8-flash"  # gemini-2.5-flash is closed to new API keys (404 NOT_FOUND)
PROMPT_VERSION = "v3"  # bump when the prompt or schema changes so old cached answers are ignored
CACHE_FILE = Path(__file__).parent / ".cache" / "analyses.json"


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
    bot_failure: Literal["not_understood", "loop", "wrong_answer", "missing_knowledge", "no_permission"]
    bot_failure_reason: str
    faq_question: str
    faq_answer: str


class AnalysisResult(BaseModel):
    analysis: Analysis
    seconds: float
    mode: Literal["llm", "offline", "cache"]
    masked_chat: str
    masked: dict[str, int]
    tokens_in: int = 0  # Gemini prompt tokens (0 offline or from cache), used for the cost estimate
    tokens_out: int = 0


def api_key() -> str | None:
    """The Gemini key: environment variable first, then Streamlit secrets (Community Cloud)."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        return st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    except Exception:  # no secrets file, or not running under Streamlit
        return None


def llm_available() -> bool:
    return bool(api_key())


def _model_name() -> str:
    """The Gemini model: GEMINI_MODEL (or the older COPILOT_MODEL) env var, then Streamlit secrets."""
    name = os.getenv("GEMINI_MODEL") or os.getenv("COPILOT_MODEL")
    if not name:
        try:
            import streamlit as st

            name = st.secrets.get("GEMINI_MODEL")
        except Exception:  # no secrets file, or not running under Streamlit
            name = None
    return (name or DEFAULT_MODEL).strip().removeprefix("models/")


MODEL = _model_name()


class SetupError(RuntimeError):
    """The model or the key is wrong, so every chat will fail the same way: stop instead of retrying."""


def _setup_error(exc: Exception) -> SetupError | None:
    code = getattr(exc, "code", None)
    text = str(exc)
    if code == 404 or "NOT_FOUND" in text:
        return SetupError(
            f"Gemini model '{MODEL}' is not available for this API key. Set another model, e.g.\n"
            '  PowerShell:  $env:GEMINI_MODEL="gemini-3.8-flash"\n'
            '  Streamlit Cloud secrets:  GEMINI_MODEL = "gemini-3.8-flash"\n'
            f"Google said: {text[:300]}"
        )
    if code in (400, 401, 403) and any(w in text for w in ("API key", "API_KEY", "PERMISSION_DENIED", "UNAUTHENTICATED")):
        return SetupError(f"Gemini rejected the API key. Check GEMINI_API_KEY.\nGoogle said: {text[:300]}")
    return None


def _build_contents(chat: str) -> list[dict]:
    contents: list[dict] = []
    for ex in FEW_SHOT:
        contents.append({"role": "user", "parts": [{"text": f"Escalated chat:\n\n{ex['chat']}"}]})
        contents.append({"role": "model", "parts": [{"text": json.dumps(ex["output"], ensure_ascii=False)}]})
    contents.append({"role": "user", "parts": [{"text": f"Escalated chat:\n\n{chat}"}]})
    return contents


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Seconds to wait after a rate-limit error: the API's own hint if present, else back off."""
    m = re.search(r"retry(?:Delay| in)\W+(\d+(?:\.\d+)?)", str(exc), re.IGNORECASE)
    return min(60.0, float(m.group(1)) + 1 if m else 5.0 * 2 ** attempt)


def analyze_llm(chat: str, retries: int = 3) -> tuple[Analysis, int, int]:
    """Return the analysis plus the prompt and output token counts Gemini reports."""
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=api_key())
    for attempt in range(retries + 1):
        try:
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
            break
        except errors.APIError as exc:  # 429 = free-tier rate limit, 503 = overloaded
            setup = _setup_error(exc)
            if setup:
                raise setup from exc
            if exc.code not in (429, 503) or attempt == retries:
                raise
            time.sleep(_retry_delay(exc, attempt))
    usage = response.usage_metadata
    tokens_in = (usage.prompt_token_count or 0) if usage else 0
    tokens_out = ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0
    if isinstance(response.parsed, Analysis):
        return response.parsed, tokens_in, tokens_out
    if response.text:
        return Analysis.model_validate_json(response.text), tokens_in, tokens_out
    raise RuntimeError("Model returned no analysis (empty or blocked response)")


def _cache_key(masked_chat: str) -> str:
    return hashlib.sha256(f"{MODEL}|{PROMPT_VERSION}|{masked_chat}".encode()).hexdigest()


def _cache_load() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cache_save(key: str, analysis: Analysis) -> None:
    data = _cache_load()
    data[key] = analysis.model_dump()
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


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


_HANDOFF_WORDS = ("operator", "оператор", "agent")


def _bot_failure_offline(chat: str, category: str) -> tuple[str, str]:
    lines = [l.strip() for l in chat.splitlines() if l.strip()]
    if lines and lines[-1].lower().startswith("bot:") and any(w in lines[-1].lower() for w in _HANDOFF_WORDS):
        lines = lines[:-1]  # the handoff itself is not the failure
    bot = [l.split(":", 1)[-1].strip() for l in lines if l.lower().startswith("bot:")]
    bot_text = " ".join(bot).lower()
    text = chat.lower()
    if any(k in bot_text for k in ("başa düşmədim", "не понял", "understand", "уточните", "bir mövzu", "choose one")):
        return "not_understood", "Bot müştərinin sualını başa düşmədiyini dedi və məsələni həll etmədi."
    if len(bot) != len(set(bot)) or any(k in text for k in ("eyni cavab", "same answer", "yenə", "опять", "снова", "again", "sayt sayt")):
        return "loop", "Bot eyni və ya ümumi cavabı təkrarladı, müştəri dövrəyə düşdü."
    if category in ("refund", "network_coverage", "internet_speed") or any(k in text for k in ("qaytar", "верните", "refund", "unblock")):
        return "no_permission", "Həll üçün hesaba giriş və ya botun edə bilmədiyi əməliyyat lazımdır."
    return "missing_knowledge", "Botun bilik bazasında bu suala dəqiq cavab yox idi."


_FAQ = {
    "billing": ("Hesabımda naməlum 'əlavə xidmət' ödənişi var, bu nədir?",
                "Hesabdakı hər xidmətin adı və qiyməti Kabinetdə 'Xərclər' bölməsində görünür. Xidməti tanımırsınızsa, sizi dərhal operatora yönləndiririk."),
    "roaming": ("Rouminq paketim hansı ölkələrdə işləyir və necə qoşulur?",
                "Ölkələrin siyahısı və qiymətlər *150# menyusunda və saytda var. Ölkəni yazsanız, sizə uyğun paketi göstərərik."),
    "tariff": ("Tarifimi dəyişsəm, bonus dəqiqələrim və internetim qalır?",
               "Tarif dəyişəndə qalıq bonuslar yeni tarifə keçmir. Dəqiq müqayisə üçün sizi operatora yönləndiririk."),
    "internet_speed": ("Telefonu yenidən başlatdım, internet hələ də yavaşdır, nə edim?",
                       "Problem davam edirsə, ünvanınız üzrə şəbəkə yoxlaması üçün texniki müraciət açılır və sizi operatora yönləndiririk."),
    "network_coverage": ("Evdə siqnal yoxdur və zənglər kəsilir, nə etməliyəm?",
                         "Ünvanınızı yazın, texniki şöbə üçün müraciət açaq. Gözləmədən operatorla danışmaq üçün sizi yönləndiririk."),
    "sim_card": ("SIM kartım bloklanıb və PUK kodum yoxdur, onlayn bərpa etmək olar?",
                 "PUK kodu şəxsiyyət təsdiqindən sonra operator tərəfindən verilir. Sizi dərhal operatora yönləndiririk."),
    "refund": ("Qoşmadığım xidmət üçün pul çıxılıb, necə geri ala bilərəm?",
               "Xidməti dərhal deaktiv edirik və geri ödəniş üçün sizi operatora yönləndiririk. Nəticə SMS ilə bildiriləcək."),
    "other": ("Bu məsələ ilə bağlı kimə müraciət edim?",
              "Sualınızı qısa yazın, sizi uyğun mütəxəssisə yönləndirək."),
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
        risk, reason = "high", f"Müştəri bunları qeyd edir: {', '.join(churn_hits[:3])}."
    elif sentiment >= 3:
        risk, reason = "medium", "Müştəri açıq-aşkar narazıdır, amma operatoru dəyişmək barədə danışmayıb."
    else:
        risk, reason = "low", "Ton sakitdir, operatoru dəyişmək barədə söz yoxdur."

    customer_lines = [l.split(":", 1)[-1].strip() for l in chat.splitlines() if l.lower().startswith(("customer", "müştəri", "клиент"))]
    first = customer_lines[0] if customer_lines else chat.strip().splitlines()[0]
    last = customer_lines[-1] if customer_lines else first
    summary = "\n".join([
        f"Problem ({CATEGORY[category]}): {first[:110]}",
        f"Söhbətdə {len(chat.splitlines())} mesaj var; bot məsələni həll edə bilməyib və operatora ötürüb.",
        f"Müştərinin son mesajı: {last[:110]}",
    ])
    failure, failure_reason = _bot_failure_offline(chat, category)
    action = "retention_offer" if risk == "high" and _ACTIONS[category] == "no_action" else _ACTIONS[category]
    return Analysis(
        summary=summary,
        category=category,
        sentiment=sentiment,
        churn_risk=risk,
        risk_reason=reason,
        suggested_reply_az=_REPLIES[category],
        next_action=action,
        bot_failure=failure,
        bot_failure_reason=failure_reason,
        faq_question=_FAQ[category][0],
        faq_answer=_FAQ[category][1],
    )


def analyze(
    chat: str,
    force_offline: bool = False,
    known_names: list[str] | None = None,
    use_cache: bool = False,
) -> AnalysisResult:
    """Mask personal data, then analyze. Falls back to offline rules if no API key is configured."""
    start = time.perf_counter()
    masked_chat, masked = mask(chat, known_names)
    tokens_in = tokens_out = 0
    if not force_offline and llm_available():
        key = _cache_key(masked_chat)
        cached = _cache_load().get(key) if use_cache else None
        if cached:
            analysis, mode = Analysis.model_validate(cached), "cache"
        else:
            (analysis, tokens_in, tokens_out), mode = analyze_llm(masked_chat), "llm"
            if use_cache:
                _cache_save(key, analysis)
    else:
        analysis, mode = analyze_offline(masked_chat), "offline"
    return AnalysisResult(
        analysis=analysis, seconds=round(time.perf_counter() - start, 2), mode=mode,
        masked_chat=masked_chat, masked=masked, tokens_in=tokens_in, tokens_out=tokens_out,
    )


if __name__ == "__main__":
    import sys

    chat_text = sys.stdin.read() if not sys.stdin.isatty() else FEW_SHOT[1]["chat"]
    print(analyze(chat_text).model_dump_json(indent=2))
