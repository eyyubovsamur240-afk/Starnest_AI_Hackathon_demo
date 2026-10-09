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
# Every Gemini answer is saved here, keyed by prompt version + masked chat, with the model that answered.
# The file is committed, so the sample chats show real Gemini output without spending the free-tier quota
# (20 requests a day per model).
CACHE_FILE = Path(__file__).parent / "results" / "gemini_cache.json"


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
    model: str | None = None  # the Gemini model that answered (None offline)


KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _key_and_source() -> tuple[str | None, str | None]:
    """The Gemini key and where it came from: environment variable first, then Streamlit secrets
    (.streamlit/secrets.toml locally, the app's Secrets on Community Cloud). No .env file is read."""
    for name in KEY_NAMES:
        if os.getenv(name):
            return os.getenv(name), f"{name} environment variable"
    try:
        import streamlit as st

        for name in KEY_NAMES:
            if st.secrets.get(name):
                return st.secrets.get(name), f"{name} in Streamlit secrets"
    except Exception:  # no secrets file, or not running under Streamlit
        pass
    return None, None


def api_key() -> str | None:
    return _key_and_source()[0]


def key_description() -> str:
    """Which key is in use, safe to print: its source and last 4 characters."""
    key, source = _key_and_source()
    return f"{source}, ending in ...{key[-4:]}" if key else "no key set"


def llm_available() -> bool:
    return bool(api_key())


def _model_names() -> list[str]:
    """The Gemini models to use, in order: GEMINI_MODEL (or the older COPILOT_MODEL) env var, then
    Streamlit secrets. A comma-separated list is a fallback chain: each model has its own free-tier quota."""
    raw = os.getenv("GEMINI_MODEL") or os.getenv("COPILOT_MODEL")
    if not raw:
        try:
            import streamlit as st

            raw = st.secrets.get("GEMINI_MODEL")
        except Exception:  # no secrets file, or not running under Streamlit
            raw = None
    names = [n.strip().removeprefix("models/") for n in (raw or DEFAULT_MODEL).split(",") if n.strip()]
    return list(dict.fromkeys(names)) or [DEFAULT_MODEL]


def _model_name() -> str:
    return _model_names()[0]


MODELS = _model_names()
MODEL = MODELS[0]  # the first choice, shown in the UI
# Models that hit their daily quota (or don't exist for this key) are skipped until this time.
_skip_until: dict[str, float] = {}


class SetupError(RuntimeError):
    """The model or the key is wrong, so every chat will fail the same way: stop instead of retrying."""

    def __init__(self, message: str, model_only: bool = False):
        super().__init__(message)
        self.model_only = model_only  # True: only this model is missing, another one may work


class QuotaError(RuntimeError):
    """The daily request quota is used up; retrying before it resets only wastes time."""

    def __init__(self, message: str, retry_seconds: float | None = None):
        super().__init__(message)
        self.retry_seconds = retry_seconds


def _setup_error(exc: Exception, model: str | None = None) -> SetupError | None:
    code = getattr(exc, "code", None)
    text = str(exc)
    if code == 404 or "NOT_FOUND" in text:
        return SetupError(
            f"Gemini model '{model or MODEL}' is not available for this API key. "
            "See the models it can use with  python eval.py --list-models  and set one, e.g.\n"
            '  PowerShell:  $env:GEMINI_MODEL="gemini-3.8-flash"\n'
            '  Streamlit Cloud secrets:  GEMINI_MODEL = "gemini-3.8-flash"\n'
            f"Google said: {text[:300]}",
            model_only=True,
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


def _retry_seconds(text: str) -> float | None:
    """The wait Google asks for: RetryInfo's retryDelay ('50515s') or 'retry in 14h1m55.5s'."""
    m = re.search(r"retryDelay\W+(\d+(?:\.\d+)?)s", text)
    if m:
        return float(m.group(1))
    m = re.search(r"retry in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+(?:\.\d+)?)s)?", text, re.IGNORECASE)
    if m and any(m.groups()):
        h, mins, secs = (float(g) if g else 0.0 for g in m.groups())
        return h * 3600 + mins * 60 + secs
    return None


def _quota_error(exc: Exception, model: str | None = None) -> QuotaError | None:
    """A 429 that will not clear within a few minutes (the free tier's daily limit)."""
    if getattr(exc, "code", None) != 429:
        return None
    text = str(exc)
    wait = _retry_seconds(text)
    if "PerDay" not in text and (wait is None or wait <= 300):
        return None  # per-minute limit: worth waiting and retrying
    hours = f" It resets in about {max(1, round(wait / 3600))} h." if wait else ""
    return QuotaError(
        f"Gemini's daily free-tier quota for {model or MODEL} is used up.{hours} The limit is per Google "
        "Cloud project and model, so a new key in the same project shares it. Saved answers still work. "
        "For more, add another model to GEMINI_MODEL (see  python eval.py --list-models) or enable billing.",
        retry_seconds=wait,
    )


UNAVAILABLE_WAITS = (5.0, 15.0, 30.0)  # seconds between retries of a 503 "high demand"


def _call_with_retries(call, minute_retries: int = 3, unavailable_retries: int = len(UNAVAILABLE_WAITS),
                       model: str | None = None):
    """Run one Gemini request. Wait and retry on a per-minute 429 (up to 3 times) or a 503 'high demand'
    (after 5, 15 and 30 s); stop at once on a daily quota, a missing model or a bad key."""
    attempts = {429: 0, 503: 0}
    while True:
        try:
            return call()
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code is None:
                raise
            setup = _setup_error(exc, model)
            if setup:
                raise setup from exc
            quota = _quota_error(exc, model)
            if quota:
                raise quota from exc
            limit = {429: minute_retries, 503: unavailable_retries}.get(code)
            if limit is None or attempts[code] >= limit:
                raise
            attempts[code] += 1
            if code == 503:
                time.sleep(UNAVAILABLE_WAITS[min(attempts[code], len(UNAVAILABLE_WAITS)) - 1])
            else:
                wait = _retry_seconds(str(exc))
                time.sleep(min(60.0, wait + 1 if wait else 5.0 * 2 ** attempts[code]))


def _ask_model(client, model: str, chat: str) -> tuple[Analysis, int, int]:
    """One Gemini request to one model. Returns the analysis plus the prompt and output token counts."""
    from google.genai import types

    response = _call_with_retries(lambda: client.models.generate_content(
        model=model,
        contents=_build_contents(chat),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Analysis,
            temperature=0.2,
        ),
    ), model=model)
    usage = response.usage_metadata
    tokens_in = (usage.prompt_token_count or 0) if usage else 0
    tokens_out = ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0
    if isinstance(response.parsed, Analysis):
        return response.parsed, tokens_in, tokens_out
    if response.text:
        return Analysis.model_validate_json(response.text), tokens_in, tokens_out
    raise RuntimeError("Model returned no analysis (empty or blocked response)")


def analyze_llm(chat: str) -> tuple[Analysis, int, int, str]:
    """Ask the models in GEMINI_MODEL in order. A model whose daily quota is used up (or that doesn't
    exist for this key) is skipped from then on; one still busy (503) after its retries is passed over
    for this chat only. Returns the analysis, token counts and the model that answered."""
    from google import genai

    client = genai.Client(api_key=api_key())
    last_exc: Exception | None = None
    for model in MODELS:
        if _skip_until.get(model, 0) > time.time():
            continue
        try:
            analysis, tokens_in, tokens_out = _ask_model(client, model, chat)
            return analysis, tokens_in, tokens_out, model
        except QuotaError as exc:
            _skip_until[model] = time.time() + (exc.retry_seconds or 3600)
            last_exc = exc
        except SetupError as exc:
            if not exc.model_only:  # a bad key fails for every model
                raise
            _skip_until[model] = time.time() + 24 * 3600
            last_exc = exc
        except Exception as exc:
            if getattr(exc, "code", None) != 503:
                raise
            last_exc = exc  # busy: try the next model for this chat
    if all(_skip_until.get(m, 0) > time.time() for m in MODELS) and not isinstance(last_exc, SetupError):
        waits = [_skip_until[m] - time.time() for m in MODELS]
        hours = max(1, round(min(waits) / 3600))
        raise QuotaError(
            f"Gemini's daily free-tier quota is used up for every model in GEMINI_MODEL ({', '.join(MODELS)}). "
            f"The first one resets in about {hours} h. Saved answers still work. To go on today, add a model "
            "with its own quota (see  python eval.py --list-models) or enable billing.",
            retry_seconds=min(waits),
        ) from last_exc
    raise last_exc or RuntimeError("No Gemini model configured")


def list_models() -> list[str]:
    """Models this key can call with generateContent (for picking a GEMINI_MODEL fallback)."""
    from google import genai

    client = genai.Client(api_key=api_key())
    names = []
    for m in client.models.list():
        if "generateContent" in (m.supported_actions or []):
            names.append((m.name or "").removeprefix("models/"))
    return sorted(n for n in names if n)


def _cache_key(masked_chat: str) -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}|{masked_chat}".encode()).hexdigest()


def _legacy_cache_keys(masked_chat: str) -> list[str]:
    """Answers saved before the model fallback were keyed by model too."""
    return [hashlib.sha256(f"{m}|{PROMPT_VERSION}|{masked_chat}".encode()).hexdigest()
            for m in dict.fromkeys([*MODELS, DEFAULT_MODEL])]


def _cache_load() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cache_get(masked_chat: str) -> dict | None:
    data = _cache_load()
    for key in [_cache_key(masked_chat), *_legacy_cache_keys(masked_chat)]:
        entry = data.get(key)
        if entry:
            return entry if "analysis" in entry else {"analysis": entry}  # oldest files: bare analysis
    return None


def _cache_save(key: str, analysis: Analysis, seconds: float, tokens_in: int, tokens_out: int,
                model: str) -> None:
    data = _cache_load()
    data[key] = {
        "model": model,
        "analysis": analysis.model_dump(),
        "seconds": seconds,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def cached_count() -> int:
    return len(_cache_load())


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
    use_cache: bool = True,
    live: bool = True,
) -> AnalysisResult:
    """Mask personal data, then analyze.

    Order: a saved Gemini answer for this chat (no API call, works without a key), then a live Gemini
    call if a key is set and `live` is on, else the offline keyword rules. `force_offline` skips Gemini
    and the cache. Raises SetupError (model or key) and QuotaError (daily limit) so callers can stop.
    """
    start = time.perf_counter()
    masked_chat, masked = mask(chat, known_names)
    tokens_in = tokens_out = 0
    seconds = model = None
    cached = _cache_get(masked_chat) if use_cache and not force_offline else None
    if cached:
        analysis, mode = Analysis.model_validate(cached["analysis"]), "cache"
        tokens_in, tokens_out = cached.get("tokens_in", 0), cached.get("tokens_out", 0)
        seconds, model = cached.get("seconds"), cached.get("model")
    elif not force_offline and live and llm_available():
        analysis, tokens_in, tokens_out, model = analyze_llm(masked_chat)
        mode = "llm"
        seconds = round(time.perf_counter() - start, 2)
        if use_cache:
            _cache_save(_cache_key(masked_chat), analysis, seconds, tokens_in, tokens_out, model)
    else:
        analysis, mode = analyze_offline(masked_chat), "offline"
    return AnalysisResult(
        analysis=analysis, seconds=seconds if seconds is not None else round(time.perf_counter() - start, 2),
        mode=mode, masked_chat=masked_chat, masked=masked, tokens_in=tokens_in, tokens_out=tokens_out,
        model=model,
    )


if __name__ == "__main__":
    import sys

    chat_text = sys.stdin.read() if not sys.stdin.isatty() else FEW_SHOT[1]["chat"]
    print(analyze(chat_text).model_dump_json(indent=2))
