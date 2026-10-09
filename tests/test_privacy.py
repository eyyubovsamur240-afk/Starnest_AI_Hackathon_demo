"""Personal data must be masked before a chat is sent to Gemini."""

import json
import re
from pathlib import Path

import pytest

from privacy import mask

TICKETS = json.loads((Path(__file__).resolve().parent.parent / "data" / "tickets.json").read_text(encoding="utf-8"))
PII_TICKETS = {"T06", "T09", "T18", "T22", "T23", "T33", "T38"}


@pytest.mark.parametrize("phone", ["+994 50 123 45 67", "050 123 45 67", "(050) 123-45-67", "0501234567"])
def test_phone_formats_are_masked(phone):
    out, counts = mask(f"nömrəm {phone}, zəng edin")
    assert "[TELEFON]" in out and counts["TELEFON"] == 1
    assert "123" not in out


def test_card_email_and_fin_are_masked():
    out, counts = mask("kart 4169 1234 5678 9012, mail leyla.m@example.az, FİN 5ABC12D")
    assert counts == {"EMAIL": 1, "KART": 1, "FİN": 1}
    assert "4169" not in out and "@" not in out and "5ABC12D" not in out


@pytest.mark.parametrize("intro", ["adım", "меня зовут", "my name is"])
def test_names_after_an_introduction_are_masked(intro):
    out, counts = mask(f"Salam, {intro} Rəşad Əliyev")
    assert "Rəşad" not in out and counts["AD"] == 1


def test_known_profile_name_is_masked_anywhere():
    out, _ = mask("Leyla xanım narazıdır, Leyla Məmmədova adına qeyd", known_names=["Leyla Məmmədova"])
    assert "Leyla" not in out and "Məmmədova" not in out


def test_plain_chat_is_left_unchanged():
    chat = "Müştəri: internet çox zəifdir\nBot: Sizi operatora yönləndirirəm."
    assert mask(chat) == (chat, {})


@pytest.mark.parametrize("ticket", [t for t in TICKETS if t["id"] in PII_TICKETS], ids=lambda t: t["id"])
def test_test_set_chats_with_personal_data_get_masked(ticket):
    out, counts = mask(ticket["chat"], [ticket["customer"]["name"]])
    assert counts, f"{ticket['id']} has personal data but nothing was masked"
    assert ticket["customer"]["name"].split()[0] not in out
    assert not re.search(r"\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)", out), "a phone number survived masking"
