"""The AZ / EN switch: every text and label exists in both languages, and every page renders in both."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import i18n
import labels_az
import labels_en
from offers import suggest
from privacy import describe

APP = str(Path(__file__).resolve().parent.parent / "app.py")
LABEL_DICTS = ["CATEGORY", "ACTION", "RISK", "SENTIMENT", "TONE", "LANGUAGE", "BOT_FAILURE", "BOT_FAILURE_FIX"]


def test_every_text_has_both_languages():
    for key, (az, en) in i18n.TEXT.items():
        assert en.strip(), key
        assert az.strip() or key == "ai_text_az", key  # the AZ UI needs no note that the AI writes in AZ


def test_english_labels_cover_the_same_codes():
    for name in LABEL_DICTS:
        assert getattr(labels_en, name).keys() == getattr(labels_az, name).keys(), name


def test_offers_and_privacy_in_english():
    offer = suggest("roaming", "high", {"tenure_years": 7, "monthly_azn": 30}, lang="en")
    assert offer.title == "Offer to keep the customer"
    assert any("loyalty" in item for item in offer.items) and offer.why.startswith("Why:")
    assert describe({"TELEFON": 1, "AD": 2}, lang="en") == "1 phone, 2 name"
    assert describe({"TELEFON": 1}) == "1 telefon"


@pytest.mark.parametrize("lang", ["az", "en"])
@pytest.mark.parametrize("page", ["app.py", "pages/1_queue.py", "pages/2_stats.py"])
def test_pages_render_in_both_languages(page, lang, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["lang"] = lang
    at.run()
    if page != "app.py":
        at.switch_page(page).run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown)
    assert ("Escalation Copilot" in text) == (lang == "en")


def test_switching_language_keeps_the_selected_chat(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].set_value("T03").run()
    at.button[0].click().run()
    at.sidebar.radio[0].set_value("en").run()
    assert not at.exception
    assert at.session_state["lang"] == "en"
    assert at.selectbox[0].value == "T03"
    assert "Churn risk" in " ".join(m.value for m in at.markdown)
