"""The analysis pipeline: test-set shape, output schema, and that the answer key never reaches the model."""

import json
from pathlib import Path

import pytest

import copilot
from copilot import Analysis, analyze
from prompts import BOT_FAILURES, CATEGORIES, RISK_LEVELS

TICKETS = json.loads((Path(__file__).resolve().parent.parent / "data" / "tickets.json").read_text(encoding="utf-8"))


def test_test_set_has_40_labelled_bot_to_customer_handoffs():
    assert len(TICKETS) == 40
    assert len({t["id"] for t in TICKETS}) == 40
    for t in TICKETS:
        lines = [line for line in t["chat"].splitlines() if line.strip()]
        assert lines[-1].startswith("Bot:"), f"{t['id']} should end with the bot handing over"
        exp = t["expected"]
        assert exp["category"] in CATEGORIES
        assert exp["churn_risk"] in RISK_LEVELS
        assert 1 <= exp["sentiment"] <= 5
        assert exp["bot_failure"] in BOT_FAILURES


@pytest.mark.parametrize("ticket", TICKETS, ids=lambda t: t["id"])
def test_offline_analysis_always_fits_the_schema(ticket):
    res = analyze(ticket["chat"], force_offline=True, known_names=[ticket["customer"]["name"]])
    assert res.mode == "offline"
    Analysis.model_validate(res.analysis.model_dump())
    assert res.analysis.summary.strip() and res.analysis.suggested_reply_az.strip()


def test_only_the_masked_chat_is_sent_to_gemini(monkeypatch):
    sent = []

    def fake_llm(chat):
        sent.append(chat)
        return copilot.analyze_offline(chat), 100, 50

    monkeypatch.setattr(copilot, "llm_available", lambda: True)
    monkeypatch.setattr(copilot, "analyze_llm", fake_llm)
    ticket = next(t for t in TICKETS if t["id"] == "T06")
    res = analyze(ticket["chat"], known_names=[ticket["customer"]["name"]])

    assert res.mode == "llm" and (res.tokens_in, res.tokens_out) == (100, 50)
    assert sent == [res.masked_chat]
    assert ticket["customer"]["name"] not in sent[0]
    assert "expected" not in sent[0] and ticket["expected"]["category"] not in sent[0].split()


def test_prompt_contents_hold_no_answer_key():
    contents = json.dumps(copilot._build_contents("Müştəri: test"), ensure_ascii=False)
    assert '"expected"' not in contents
