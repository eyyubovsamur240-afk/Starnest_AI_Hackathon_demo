"""Retention offers are rule-based, so the model never invents discounts."""

from offers import suggest

LOYAL = {"tenure_years": 7, "monthly_azn": 10}
NEW_CHEAP = {"tenure_years": 1, "monthly_azn": 10}
NEW_VALUABLE = {"tenure_years": 1, "monthly_azn": 40}


def test_no_offer_for_low_risk():
    assert suggest("billing", "low", LOYAL) is None


def test_medium_risk_gets_an_offer_only_if_loyal_or_valuable():
    assert suggest("billing", "medium", NEW_CHEAP) is None
    assert suggest("billing", "medium", LOYAL) is not None
    assert suggest("billing", "medium", NEW_VALUABLE) is not None


def test_high_risk_always_gets_a_priced_offer():
    offer = suggest("internet_speed", "high", NEW_CHEAP)
    assert offer is not None and offer.cost_azn > 0
    assert offer.customer_value_azn == 120
    assert any("menecer" in item for item in offer.items)


def test_loyalty_discount_is_added_for_long_term_customers():
    offer = suggest("roaming", "high", LOYAL)
    assert any("sadiqlik" in item for item in offer.items)


def test_unknown_category_and_missing_profile_fall_back_safely():
    offer = suggest("something_new", "high", None)
    assert offer is not None and offer.cost_azn > 0
