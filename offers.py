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


@dataclass
class Offer:
    title: str
    items: list[str]
    cost_azn: float
    customer_value_azn: float | None
    why: str


def suggest(category: str, churn_risk: str, profile: dict | None) -> Offer | None:
    """Return an offer, or None when the customer is not at risk."""
    tenure = (profile or {}).get("tenure_years", 0)
    monthly = (profile or {}).get("monthly_azn")
    loyal = tenure >= 5
    valuable = monthly is not None and monthly >= 25

    if churn_risk == "low" or (churn_risk == "medium" and not (loyal or valuable)):
        return None

    text, cost = _BY_CATEGORY.get(category, _BY_CATEGORY["other"])
    if cost is None:  # offers priced off the monthly fee
        cost = round((monthly or 15) * (0.5 if category == "network_coverage" else 0.3 * 6), 1)
    items = [text]
    reasons = [f"risk {'yüksəkdir' if churn_risk == 'high' else 'ortadır'}"]

    if loyal:
        items.append(f"{tenure} illik sadiqlik üçün 3 ay 15% endirim")
        cost += round((monthly or 15) * 0.15 * 3, 1)
        reasons.append(f"{tenure} ildir müştəridir")
    if valuable:
        reasons.append(f"aylıq ödənişi {monthly} AZN-dir")
    if churn_risk == "high" and not loyal:
        items.append("Şəxsi menecer: növbəti 30 gün müraciətləri növbəsiz")

    value = monthly * 12 if monthly else None
    title = "Müştərini saxlamaq üçün təklif" if churn_risk == "high" else "Sadiq müştəri üçün jest"
    return Offer(title=title, items=items, cost_azn=round(cost, 1), customer_value_azn=value,
                 why="Səbəb: " + ", ".join(reasons) + ".")
