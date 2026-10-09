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
        return copilot.analyze_offline(chat), 1200, 300

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

    monkeypatch.setattr(copilot, "llm_available", lambda: False)  # judges without a key
    assert copilot.analyze(chat).mode == "cache"
    assert copilot.analyze(TICKETS[1]["chat"]).mode == "offline"


def test_live_false_and_offline_mode_never_call_gemini(fake_gemini):
    assert copilot.analyze(TICKETS[0]["chat"], live=False).mode == "offline"
    copilot.analyze(TICKETS[0]["chat"])
    assert copilot.analyze(TICKETS[0]["chat"], force_offline=True).mode == "offline"
    assert len(fake_gemini) == 1


def test_old_cache_format_is_still_read(monkeypatch):
    masked, _ = copilot.mask(TICKETS[0]["chat"])
    analysis = copilot.analyze_offline(masked).model_dump()
    copilot.CACHE_FILE.write_text(json.dumps({copilot._cache_key(masked): analysis}), encoding="utf-8")
    assert copilot.analyze(TICKETS[0]["chat"]).mode == "cache"


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


def test_503_is_retried_once(monkeypatch):
    monkeypatch.setattr(copilot.time, "sleep", lambda s: None)
    call, calls = _flaky([FakeAPIError(503, BUSY_503)])
    assert copilot._call_with_retries(call) == "ok" and len(calls) == 2

    call, calls = _flaky([FakeAPIError(503, BUSY_503)] * 2)
    with pytest.raises(FakeAPIError):
        copilot._call_with_retries(call)
    assert len(calls) == 2


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
    assert "PARTIAL: 2 of 5" in (tmp_path / "eval_llm.md").read_text(encoding="utf-8")
