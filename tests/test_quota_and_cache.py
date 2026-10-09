"""Free-tier limits: one request per chat, saved answers reused, clear stops on quota and model errors."""

import json
from pathlib import Path

import pytest

import copilot

TICKETS = json.loads((Path(__file__).resolve().parent.parent / "data" / "tickets.json").read_text(encoding="utf-8"))

# Shortened from the real 429 Gemini returned on 2026-10-09.
DAILY_429 = (
    "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota. "
    "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, "
    "model: gemini-3.8-flash\\nPlease retry in 14h1m55.597453287s.', 'details': [{'quotaId': "
    "'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaValue': '20'}, {'@type': "
    "'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '50515s'}]}}"
)
MINUTE_429 = "429 RESOURCE_EXHAUSTED. quotaId: 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', retryDelay: '20s'"
BUSY_503 = "503 UNAVAILABLE. This model is currently experiencing high demand."


class FakeAPIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@pytest.fixture
def fake_gemini(monkeypatch):
    calls = []

    def fake_llm(chat):
        calls.append(chat)
        return copilot.analyze_offline(chat), 1200, 300, "gemini-test-flash"

    monkeypatch.setattr(copilot, "llm_available", lambda: True)
    monkeypatch.setattr(copilot, "analyze_llm", fake_llm)
    return calls


def test_each_chat_is_sent_to_gemini_once_then_read_from_the_saved_answers(fake_gemini, monkeypatch):
    chat = TICKETS[0]["chat"]
    first = copilot.analyze(chat)
    second = copilot.analyze(chat)
    assert len(fake_gemini) == 1
    assert (first.mode, second.mode) == ("llm", "cache")
    assert (second.tokens_in, second.tokens_out) == (1200, 300)
    assert second.seconds == first.seconds
    assert first.model == second.model == "gemini-test-flash"

    monkeypatch.setattr(copilot, "llm_available", lambda: False)  # judges without a key
    assert copilot.analyze(chat).mode == "cache"
    assert copilot.analyze(TICKETS[1]["chat"]).mode == "offline"


def test_live_false_and_offline_mode_never_call_gemini(fake_gemini):
    assert copilot.analyze(TICKETS[0]["chat"], live=False).mode == "offline"
    copilot.analyze(TICKETS[0]["chat"])
    assert copilot.analyze(TICKETS[0]["chat"], force_offline=True).mode == "offline"
    assert len(fake_gemini) == 1


def test_old_cache_formats_are_still_read(monkeypatch):
    masked, _ = copilot.mask(TICKETS[0]["chat"])
    analysis = copilot.analyze_offline(masked).model_dump()
    copilot.CACHE_FILE.write_text(json.dumps({copilot._cache_key(masked): analysis}), encoding="utf-8")
    assert copilot.analyze(TICKETS[0]["chat"]).mode == "cache"

    # answers saved before the model fallback were keyed by model too
    legacy = copilot._legacy_cache_keys(masked)[-1]
    entry = {"model": copilot.DEFAULT_MODEL, "analysis": analysis, "seconds": 20.0, "tokens_in": 1, "tokens_out": 2}
    copilot.CACHE_FILE.write_text(json.dumps({legacy: entry}), encoding="utf-8")
    res = copilot.analyze(TICKETS[0]["chat"])
    assert (res.mode, res.model, res.seconds) == ("cache", copilot.DEFAULT_MODEL, 20.0)


def test_daily_quota_is_a_quota_error_but_a_per_minute_limit_is_not():
    err = copilot._quota_error(FakeAPIError(429, DAILY_429))
    assert isinstance(err, copilot.QuotaError) and err.retry_seconds == 50515
    assert copilot._quota_error(FakeAPIError(429, MINUTE_429)) is None
    assert copilot._retry_seconds("Please retry in 14h1m55.5s.") == pytest.approx(50515.5)


def _flaky(errors, result="ok"):
    calls = []

    def call():
        calls.append(1)
        if len(calls) <= len(errors):
            raise errors[len(calls) - 1]
        return result

    return call, calls


def test_503_is_retried_after_5_15_and_30_seconds(monkeypatch):
    waits = []
    monkeypatch.setattr(copilot.time, "sleep", waits.append)
    call, calls = _flaky([FakeAPIError(503, BUSY_503)])
    assert copilot._call_with_retries(call) == "ok" and len(calls) == 2

    waits.clear()
    call, calls = _flaky([FakeAPIError(503, BUSY_503)] * 4)
    with pytest.raises(FakeAPIError):
        copilot._call_with_retries(call)
    assert len(calls) == 4 and waits == [5.0, 15.0, 30.0]


def test_daily_quota_stops_without_retrying(monkeypatch):
    monkeypatch.setattr(copilot.time, "sleep", lambda s: pytest.fail("must not wait for a daily quota"))
    call, calls = _flaky([FakeAPIError(429, DAILY_429)])
    with pytest.raises(copilot.QuotaError):
        copilot._call_with_retries(call)
    assert len(calls) == 1


def test_eval_writes_a_partial_report_when_the_quota_runs_out(monkeypatch, tmp_path):
    import eval as eval_script

    done = []

    def analyze_until_quota(chat, **kwargs):
        if kwargs.get("force_offline"):  # the keyword-rule comparison on the same chat
            return copilot.analyze(chat, **kwargs)
        if len(done) == 2:
            raise copilot.QuotaError("Gemini's daily free-tier quota is used up.", 50515)
        done.append(chat)
        return copilot.analyze(chat, force_offline=True).model_copy(update={"mode": "llm"})

    monkeypatch.setattr(eval_script, "OUT_DIR", tmp_path)
    monkeypatch.setattr(eval_script, "llm_available", lambda: True)
    monkeypatch.setattr(eval_script, "analyze", analyze_until_quota)
    monkeypatch.setattr("sys.argv", ["eval.py", "--limit", "5"])
    with pytest.raises(SystemExit, match="quota"):
        eval_script.main()

    summary = json.loads((tmp_path / "eval_llm.json").read_text(encoding="utf-8"))["summary"]
    assert summary["partial"] and summary["tickets"] == 2 and len(summary["not_run"]) == 3
    md = (tmp_path / "eval_llm.md").read_text(encoding="utf-8")
    assert "Gemini on 2 of 5 chats, a sample" in md
    assert "Keyword rules (same 2 chats)" in md
    assert set(summary["offline_on_same_chats"]) == {
        "category_accuracy", "churn_risk_accuracy", "sentiment_within_1", "bot_failure_accuracy"}


def test_key_description_names_the_source_and_hides_the_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSy-secret-part-WXYZ")
    text = copilot.key_description()
    assert text == "GEMINI_API_KEY environment variable, ending in ...WXYZ"
    assert "secret" not in text


def test_gemini_api_key_wins_over_google_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "old-key-1111")
    monkeypatch.setenv("GEMINI_API_KEY", "new-key-2222")
    assert copilot.api_key() == "new-key-2222"
    assert copilot.key_description().endswith("...2222")


class _FakeResponse:
    def __init__(self, analysis):
        self.parsed, self.text, self.usage_metadata = analysis, None, None


@pytest.fixture
def two_models(monkeypatch):
    """GEMINI_MODEL="model-a,model-b" with a fake client; `behaviour[model]` decides each answer."""
    behaviour, calls = {}, []
    answer = copilot.analyze_offline(TICKETS[0]["chat"])

    def generate_content(model, **kwargs):
        calls.append(model)
        error = behaviour.get(model)
        if error:
            raise error
        return _FakeResponse(answer)

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = type("Models", (), {"generate_content": staticmethod(generate_content)})()

    import google.genai

    monkeypatch.setattr(google.genai, "Client", FakeClient)
    monkeypatch.setattr(copilot, "MODELS", ["model-a", "model-b"])
    monkeypatch.setattr(copilot, "_skip_until", {})
    monkeypatch.setattr(copilot.time, "sleep", lambda s: None)
    return behaviour, calls


def test_daily_quota_moves_to_the_next_model_and_skips_the_first_from_then_on(two_models):
    behaviour, calls = two_models
    behaviour["model-a"] = FakeAPIError(429, DAILY_429)
    assert copilot.analyze_llm("chat")[3] == "model-b"
    assert copilot.analyze_llm("chat 2")[3] == "model-b"
    assert calls == ["model-a", "model-b", "model-b"]


def test_a_model_still_busy_after_its_retries_is_passed_over_for_that_chat(two_models):
    behaviour, calls = two_models
    behaviour["model-a"] = FakeAPIError(503, BUSY_503)
    assert copilot.analyze_llm("chat")[3] == "model-b"
    assert calls == ["model-a"] * 4 + ["model-b"]
    behaviour.pop("model-a")
    assert copilot.analyze_llm("chat 2")[3] == "model-a"  # busy is not remembered


def test_quota_error_only_when_every_model_is_used_up(two_models):
    behaviour, _ = two_models
    behaviour["model-a"] = behaviour["model-b"] = FakeAPIError(429, DAILY_429)
    with pytest.raises(copilot.QuotaError, match="every model"):
        copilot.analyze_llm("chat")


def test_a_bad_key_stops_at_once_but_a_missing_model_falls_through(two_models):
    behaviour, calls = two_models
    behaviour["model-a"] = FakeAPIError(404, "404 NOT_FOUND. models/model-a is not found")
    assert copilot.analyze_llm("chat")[3] == "model-b"
    behaviour["model-b"] = FakeAPIError(403, "403 PERMISSION_DENIED. API key not valid")
    with pytest.raises(copilot.SetupError):
        copilot.analyze_llm("chat 2")


def test_model_list_comes_from_gemini_model(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "models/gemini-a-flash, gemini-b-flash-lite,gemini-a-flash")
    assert copilot._model_names() == ["gemini-a-flash", "gemini-b-flash-lite"]
