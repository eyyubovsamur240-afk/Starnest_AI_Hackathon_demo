"""English display labels for the UI, keyed by the same internal codes as labels_az.py."""

from labels_az import ACTION_ICON, BOT_FAILURE_ICON  # noqa: F401  (icons are the same in both languages)

CATEGORY = {
    "billing": "Billing and payments",
    "roaming": "Roaming",
    "tariff": "Tariffs and packages",
    "internet_speed": "Internet speed",
    "network_coverage": "Network coverage",
    "sim_card": "SIM card",
    "refund": "Refund",
    "other": "Other",
}

ACTION = {
    "refund": "Refund the money",
    "tariff_change": "Change the tariff",
    "escalate_to_tech": "Escalate to the technical team",
    "unblock_sim": "Unblock the SIM card",
    "explain_charges": "Explain the charges",
    "retention_offer": "Make an offer to keep the customer",
    "no_action": "No further step needed",
}

RISK = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}

SENTIMENT = {1: "calm", 2: "slightly unhappy", 3: "unhappy", 4: "angry", 5: "very angry"}

TONE = {"calm": "calm", "annoyed": "annoyed", "furious": "furious"}

LANGUAGE = {"az": "AZ", "ru": "RU", "en": "EN", "mixed": "mixed"}

BOT_FAILURE = {
    "not_understood": "The bot didn't understand the question",
    "loop": "The bot repeated the same answer",
    "wrong_answer": "The bot gave a wrong answer",
    "missing_knowledge": "The bot lacked the information",
    "no_permission": "The bot isn't allowed to do this",
}

# What the team should change so the bot handles this case next time.
BOT_FAILURE_FIX = {
    "not_understood": "Add these phrases to the bot's language model (AZ/RU/EN, misspellings included).",
    "loop": "After giving the same answer twice, the bot should hand over to an agent at once.",
    "wrong_answer": "Check and fix the bot's answer rule for this scenario.",
    "missing_knowledge": "Add the question and answer below to the bot's knowledge base.",
    "no_permission": "The bot needs a system integration for this action, or should hand over to an agent straight away.",
}
