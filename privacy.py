"""Mask personal data in a chat before it leaves the machine (sent to Gemini).

Rule-based: phone numbers, card numbers, e-mails, FIN codes and names. Names are caught
after phrases like "adım ..." / "меня зовут ..." / "my name is ...", plus any name the
CRM profile already knows. It is a safety net for the demo, not a certified anonymiser.
"""

from __future__ import annotations

import re

LABELS = {
    "TELEFON": "telefon",
    "KART": "kart nömrəsi",
    "EMAIL": "e-poçt",
    "FİN": "FİN kod",
    "AD": "ad",
}

LABELS_EN = {"TELEFON": "phone", "KART": "card number", "EMAIL": "e-mail", "FİN": "FIN code", "AD": "name"}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CARD = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")
# +994 50 123 45 67, 050 123 45 67, (050) 123-45-67, 0501234567
_PHONE = re.compile(r"(?<!\d)(?:\+?994[\s-]?|0)\(?\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")
# FIN code: 7 Latin capitals and digits, with at least one of each.
_FIN = re.compile(r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{7}\b")

_NAME_WORD = r"[A-ZÇƏĞİÖŞÜА-ЯЁ][a-zçəğıöşüа-яё]+\b"
_NAME_INTRO = re.compile(
    r"(?i:\b(?:mənim adım|adım|меня зовут|my name is))\s+"
    rf"({_NAME_WORD}(?:\s+{_NAME_WORD})?)"
)


def mask(text: str, known_names: list[str] | None = None) -> tuple[str, dict[str, int]]:
    """Return the masked text and how many items of each kind were hidden."""
    counts: dict[str, int] = {}

    def sub(pattern: re.Pattern, tag: str, s: str, group: int = 0) -> str:
        def repl(m: re.Match) -> str:
            counts[tag] = counts.get(tag, 0) + 1
            if group:
                return m.group(0).replace(m.group(group), f"[{tag}]")
            return f"[{tag}]"
        return pattern.sub(repl, s)

    out = sub(_EMAIL, "EMAIL", text)
    out = sub(_CARD, "KART", out)
    out = sub(_PHONE, "TELEFON", out)
    out = sub(_FIN, "FİN", out)
    out = sub(_NAME_INTRO, "AD", out, group=1)
    for name in known_names or []:
        # Full name first so "Leyla Məmmədova" becomes one [AD], then each part on its own.
        for part in [name] + sorted(set(name.split()), key=len, reverse=True):
            if len(part) >= 3:
                out = sub(re.compile(rf"\b{re.escape(part)}\b", re.IGNORECASE), "AD", out)
    return out, counts


def describe(counts: dict[str, int], lang: str = "az") -> str:
    """One-liner, e.g. '1 telefon, 2 ad' (or '1 phone, 2 name' with lang="en")."""
    labels = LABELS_EN if lang == "en" else LABELS
    return ", ".join(f"{n} {labels[tag]}" for tag, n in counts.items() if n)
