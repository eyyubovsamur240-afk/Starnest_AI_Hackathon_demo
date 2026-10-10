"""Retention offers for customers at risk of leaving.

Rule-based on purpose: the agent can see exactly why an offer was suggested, and the
model never invents discounts. Profiles and offers are made up for the demo.
"""

from __future__ import annotations

from dataclasses import dataclass

# Main offer per issue category: (text, approximate cost in AZN).
_BY_CATEGORY = {
    "internet_speed": ("Problem həll olunana qədər hər ay +20 GB pulsuz internet", 5),
    "network_coverage": ("Texniki yoxlama bitənə qədər abunə haqqının 50%-i geri", None),
    "billing": ("Səhv tutulan məbləğin qaytarılması və üzərinə 5 AZN bonus balans", 5),
    "refund": ("Məbləğin qaytarılması və üzərinə 5 AZN bonus balans", 5),
    "tariff": ("Köhnə tarif şərtlərinin 6 ay saxlanması", None),
    "roaming": ("Növbəti səfər üçün 3 GB pulsuz rouminq paketi", 8),
    "sim_card": ("Pulsuz SIM/eSIM bərpası və kuryerlə ünvana çatdırılma", 3),
    "other": ("Növbəti ay üçün 5 AZN bonus balans", 5),
}

_BY_CATEGORY_EN = {
    "internet_speed": "+20 GB free internet every month until the problem is fixed",
    "network_coverage": "50% of the monthly fee back until the technical check is done",
    "billing": "Refund of the wrong charge plus a 5 AZN bonus balance",
    "refund": "Refund of the amount plus a 5 AZN bonus balance",
    "tariff": "Keep the old tariff terms for 6 months",
    "roaming": "A free 3 GB roaming package for the next trip",
    "sim_card": "Free SIM/eSIM replacement delivered by courier",
    "other": "A 5 AZN bonus balance for next month",
}

_TEXT = {
    "az": {
        "risk_high": "risk yüksəkdir", "risk_medium": "risk ortadır",
        "loyal_item": "{t} illik sadiqlik üçün 3 ay 15% endirim", "loyal_reason": "{t} ildir müştəridir",
        "valuable": "aylıq ödənişi {m} AZN-dir", "manager": "Şəxsi menecer: növbəti 30 gün müraciətləri növbəsiz",
        "title_high": "Müştərini saxlamaq üçün təklif", "title_medium": "Sadiq müştəri üçün jest", "why": "Səbəb: ",
    },
    "en": {
        "risk_high": "risk is high", "risk_medium": "risk is medium",
        "loyal_item": "15% off for 3 months for {t} years of loyalty", "loyal_reason": "customer for {t} years",
        "valuable": "pays {m} AZN a month", "manager": "Personal manager: no queue for the next 30 days",
        "title_high": "Offer to keep the customer", "title_medium": "A gesture for a loyal customer", "why": "Why: ",
    },
}


@dataclass
class Offer:
    title: str
    items: list[str]
    cost_azn: float
    customer_value_azn: float | None
    why: str


def suggest(category: str, churn_risk: str, profile: dict | None, lang: str = "az") -> Offer | None:
    """Return an offer, or None when the customer is not at risk. `lang` is "az" or "en"."""
    tx = _TEXT["en" if lang == "en" else "az"]
    tenure = (profile or {}).get("tenure_years", 0)
    monthly = (profile or {}).get("monthly_azn")
    loyal = tenure >= 5
    valuable = monthly is not None and monthly >= 25

    if churn_risk == "low" or (churn_risk == "medium" and not (loyal or valuable)):
        return None

    text, cost = _BY_CATEGORY.get(category, _BY_CATEGORY["other"])
    if cost is None:  # offers priced off the monthly fee
        cost = round((monthly or 15) * (0.5 if category == "network_coverage" else 0.3 * 6), 1)
    if lang == "en":
        text = _BY_CATEGORY_EN.get(category, _BY_CATEGORY_EN["other"])
    items = [text]
    reasons = [tx["risk_high"] if churn_risk == "high" else tx["risk_medium"]]

    if loyal:
        items.append(tx["loyal_item"].format(t=tenure))
        cost += round((monthly or 15) * 0.15 * 3, 1)
        reasons.append(tx["loyal_reason"].format(t=tenure))
    if valuable:
        reasons.append(tx["valuable"].format(m=monthly))
    if churn_risk == "high" and not loyal:
        items.append(tx["manager"])

    value = monthly * 12 if monthly else None
    title = tx["title_high"] if churn_risk == "high" else tx["title_medium"]
    return Offer(title=title, items=items, cost_azn=round(cost, 1), customer_value_azn=value,
                 why=tx["why"] + ", ".join(reasons) + ".")
